# validator.py
import sqlite3
import calendar
import json
from datetime import date

from database import get_connection


WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6
}


def parse_operating_days(value):
    """Convert operating days into weekday numbers (Monday=0, Sunday=6)."""

    if not value:
        return set()

    try:
        days = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        days = str(value).replace("[", "").replace("]", "").split(",")

    if not isinstance(days, (list, tuple, set)):
        days = [days]

    result = set()

    for day in days:
        text = str(day).strip().lower()

        if text in WEEKDAYS:
            result.add(WEEKDAYS[text])
        else:
            try:
                number = int(text)
                if 0 <= number <= 6:
                    result.add(number)
            except ValueError:
                pass

    return result


def get_required_staff(rule, weekday):
    """Return the staffing requirement for a particular weekday."""

    required = rule["min_staffing"]

    try:
        daily_staffing = json.loads(rule["daily_staffing"] or "{}")
        required = int(daily_staffing.get(str(weekday), required))
    except (json.JSONDecodeError, TypeError, ValueError):
        required = int(rule["min_staffing"])

    return required


def validate_month_roster(year, month):
    """
    Validate a generated monthly roster.

    Returns a list of dictionaries containing all detected issues.
    """

    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    conflicts = []

    try:
        # 1. Fetch all roster entries for the selected month.
        start_date = f"{year}-{month:02d}-01"
        last_day = calendar.monthrange(year, month)[1]
        end_date = f"{year}-{month:02d}-{last_day:02d}"

        cursor.execute("""
            SELECT
                r.roster_id,
                r.assignment_id,
                r.employee_id,
                r.brand_id,
                r.process_id,
                r.roster_date,
                e.employee_name,
                b.brand_name,
                p.process_name
            FROM roster_entries r
            JOIN employees e ON r.employee_id = e.employee_id
            JOIN brands b ON r.brand_id = b.brand_id
            JOIN processes p ON r.process_id = p.process_id
            WHERE r.roster_date BETWEEN ? AND ?
        """, (start_date, end_date))

        roster = [dict(row) for row in cursor.fetchall()]

        # 2. Fetch weekly offs.
        cursor.execute("""
            SELECT employee_id, weekday
            FROM employee_weekly_offs
        """)
        weekly_offs = {}

        for row in cursor.fetchall():
            weekly_offs.setdefault(row["employee_id"], set()).add(
                row["weekday"]
            )

        # 3. Fetch approved leaves and comp-offs.
        cursor.execute("""
            SELECT employee_id, leave_date, leave_type
            FROM leaves
            WHERE status = 'Approved'
              AND leave_date BETWEEN ? AND ?
        """, (start_date, end_date))

        approved_leaves = {
            (row["employee_id"], row["leave_date"]): row["leave_type"]
            for row in cursor.fetchall()
        }

        # 4. Fetch company holidays.
        cursor.execute("""
            SELECT holiday_date, holiday_name
            FROM holidays
            WHERE holiday_date BETWEEN ? AND ?
        """, (start_date, end_date))

        holidays = {
            row["holiday_date"]: row["holiday_name"]
            for row in cursor.fetchall()
        }

        # 5. Fetch active brand-process operating rules.
        cursor.execute("""
            SELECT
                r.brand_id,
                r.process_id,
                r.operating_days,
                r.min_staffing,
                r.holiday_policy,
                r.daily_staffing,
                b.brand_name,
                p.process_name
            FROM brand_process_rules r
            JOIN brands b ON r.brand_id = b.brand_id
            JOIN processes p ON r.process_id = p.process_id
            WHERE b.is_active = 1
        """)

        rules = [dict(row) for row in cursor.fetchall()]

        rule_lookup = {
            (rule["brand_id"], rule["process_id"]): rule
            for rule in rules
        }

        # -------------------------------------------------
        # CHECK 1: Employee double booking on the same day
        # -------------------------------------------------
        employee_daily_count = {}

        for entry in roster:
            key = (entry["employee_id"], entry["roster_date"])
            employee_daily_count.setdefault(key, []).append(entry)

        for (employee_id, roster_date), entries in employee_daily_count.items():
            if len(entries) > 1:
                conflicts.append({
                    "Date": roster_date,
                    "Employee": entries[0]["employee_name"],
                    "Brand": "Multiple",
                    "Process": "Multiple",
                    "Issue": "Double Booking: Employee assigned more than once on the same day",
                    "Required": 1,
                    "Assigned": len(entries)
                })

        # -------------------------------------------------
        # CHECK 2: Weekly off, leave and holiday violations
        # -------------------------------------------------
        for entry in roster:
            employee_id = entry["employee_id"]
            roster_date = entry["roster_date"]
            weekday = date.fromisoformat(roster_date).weekday()

            common = {
                "Date": roster_date,
                "Employee": entry["employee_name"],
                "Brand": entry["brand_name"],
                "Process": entry["process_name"],
                "Required": 0,
                "Assigned": 1
            }

            if weekday in weekly_offs.get(employee_id, set()):
                conflicts.append({
                    **common,
                    "Issue": "Weekly Off Violation"
                })

            leave_key = (employee_id, roster_date)

            if leave_key in approved_leaves:
                conflicts.append({
                    **common,
                    "Issue": f"Approved {approved_leaves[leave_key]} Violation"
                })

            if roster_date in holidays:
                rule = rule_lookup.get(
                    (entry["brand_id"], entry["process_id"])
                )

                if rule and rule["holiday_policy"] == "OFF":
                    conflicts.append({
                        **common,
                        "Issue": f"Holiday Violation: {holidays[roster_date]}"
                    })

        # -------------------------------------------------
        # CHECK 3: Non-operating day assignments
        # -------------------------------------------------
        for entry in roster:
            rule = rule_lookup.get(
                (entry["brand_id"], entry["process_id"])
            )

            if not rule:
                continue

            weekday = date.fromisoformat(entry["roster_date"]).weekday()
            operating_days = parse_operating_days(rule["operating_days"])

            if weekday not in operating_days:
                conflicts.append({
                    "Date": entry["roster_date"],
                    "Employee": entry["employee_name"],
                    "Brand": entry["brand_name"],
                    "Process": entry["process_name"],
                    "Issue": "Non-Operating Day Violation",
                    "Required": 0,
                    "Assigned": 1
                })

        # -------------------------------------------------
        # CHECK 4: Minimum staffing for every operating day
        # -------------------------------------------------
        roster_counts = {}

        for entry in roster:
            key = (
                entry["roster_date"],
                entry["brand_id"],
                entry["process_id"]
            )
            roster_counts[key] = roster_counts.get(key, 0) + 1

        for day_number in range(1, last_day + 1):
            current_date = date(year, month, day_number)
            date_text = current_date.isoformat()
            weekday = current_date.weekday()

            for rule in rules:
                operating_days = parse_operating_days(
                    rule["operating_days"]
                )

                if weekday not in operating_days:
                    continue

                if (
                    date_text in holidays
                    and rule["holiday_policy"] == "OFF"
                ):
                    continue

                required = get_required_staff(rule, weekday)

                assigned = roster_counts.get(
                    (date_text, rule["brand_id"], rule["process_id"]),
                    0
                )

                if assigned < required:
                    conflicts.append({
                        "Date": date_text,
                        "Employee": "-",
                        "Brand": rule["brand_name"],
                        "Process": rule["process_name"],
                        "Issue": "Minimum Staffing Shortage",
                        "Required": required,
                        "Assigned": assigned
                    })

        # -------------------------------------------------
        # CHECK 5: Duplicate assignment on the same day
        # -------------------------------------------------
        assignment_count = {}

        for entry in roster:
            key = (entry["assignment_id"], entry["roster_date"])
            assignment_count[key] = assignment_count.get(key, 0) + 1

        for entry in roster:
            key = (entry["assignment_id"], entry["roster_date"])

            if assignment_count[key] > 1:
                conflicts.append({
                    "Date": entry["roster_date"],
                    "Employee": entry["employee_name"],
                    "Brand": entry["brand_name"],
                    "Process": entry["process_name"],
                    "Issue": "Duplicate Assignment",
                    "Required": 1,
                    "Assigned": assignment_count[key]
                })

        return conflicts

    finally:
        conn.close()