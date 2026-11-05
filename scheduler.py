
import calendar
import json
from datetime import date, timedelta

from database import get_connection


def generate_month_roster(year, month):

    conn = get_connection()

    try:
        cursor = conn.cursor()

        start_date = date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        end_date = date(year, month, last_day)

        # ------------------------------------------
        # 1. LOAD BRAND-PROCESS RULES
        # ------------------------------------------

        rules = cursor.execute("""
            SELECT
                r.rule_id,
                r.brand_id,
                b.brand_name,
                r.process_id,
                p.process_name,
                r.operating_days,
                r.min_staffing,
                r.holiday_policy,
                r.daily_staffing
            FROM brand_process_rules r
            JOIN brands b ON r.brand_id = b.brand_id
            JOIN processes p ON r.process_id = p.process_id
            WHERE b.is_active = 1
        """).fetchall()

        if not rules:
            return {
                "success": False,
                "message": "No brand-process rules found.",
                "generated": 0,
                "conflicts": 0
            }

        # ------------------------------------------
        # 2. LOAD EMPLOYEE ASSIGNMENTS
        # ------------------------------------------

        assignments = cursor.execute("""
            SELECT
                a.assignment_id,
                a.employee_id,
                a.brand_id,
                a.process_id
            FROM assignments a
            JOIN employees e
                ON a.employee_id = e.employee_id
            WHERE e.is_active = 1
        """).fetchall()

        assignment_map = {}

        for assignment_id, employee_id, brand_id, process_id in assignments:

            key = (brand_id, process_id)

            assignment_map.setdefault(key, []).append(
                (assignment_id, employee_id)
            )

        # ------------------------------------------
        # 3. LOAD WEEKLY OFFS
        # ------------------------------------------

        weekly_offs = cursor.execute("""
            SELECT employee_id, weekday
            FROM employee_weekly_offs
        """).fetchall()

        weekly_off_map = {}

        for employee_id, weekday in weekly_offs:

            weekly_off_map.setdefault(
                employee_id, set()
            ).add(weekday)

        # ------------------------------------------
        # 4. LOAD APPROVED LEAVES AND COMP-OFFS
        # ------------------------------------------

        leaves = cursor.execute("""
            SELECT employee_id, leave_date
            FROM leaves
            WHERE status = 'Approved'
        """).fetchall()

        leave_map = set(leaves)

        # ------------------------------------------
        # 5. LOAD COMPANY HOLIDAYS
        # ------------------------------------------

        holidays = cursor.execute("""
            SELECT holiday_date
            FROM holidays
        """).fetchall()

        holiday_dates = {row[0] for row in holidays}

        # ------------------------------------------
        # 6. REPLACE EXISTING ROSTER FOR THIS MONTH
        # ------------------------------------------

        cursor.execute("BEGIN")

        cursor.execute("""
            DELETE FROM roster_conflicts
            WHERE roster_date BETWEEN ? AND ?
        """, (start_date.isoformat(), end_date.isoformat()))

        cursor.execute("""
            DELETE FROM roster_entries
            WHERE roster_date BETWEEN ? AND ?
        """, (start_date.isoformat(), end_date.isoformat()))

        monthly_employee_load = {}

        generated_count = 0
        conflict_count = 0

        # ------------------------------------------
        # 7. GENERATE DAILY ROSTER
        # ------------------------------------------

        current_date = start_date

        while current_date <= end_date:

            roster_date = current_date.isoformat()
            weekday = current_date.weekday()

            is_holiday = roster_date in holiday_dates

            daily_tasks = []

            for rule in rules:

                (
                    rule_id,
                    brand_id,
                    brand_name,
                    process_id,
                    process_name,
                    operating_days_json,
                    min_staffing,
                    holiday_policy,
                    daily_staffing_json
                ) = rule

                operating_days = json.loads(
                    operating_days_json
                )

                # Check operating day
                if weekday not in operating_days:
                    continue

                # Check holiday policy
                if is_holiday and holiday_policy != "WORK":
                    continue

                # Check daily staffing override
                daily_staffing = json.loads(
                    daily_staffing_json or "{}"
                )

                required_staff = int(
                    daily_staffing.get(
                        str(weekday),
                        min_staffing
                    )
                )

                candidates = assignment_map.get(
                    (brand_id, process_id), []
                )

                eligible = []

                for assignment_id, employee_id in candidates:

                    # Employee weekly off
                    if weekday in weekly_off_map.get(
                        employee_id, set()
                    ):
                        continue

                    # Approved leave or comp-off
                    if (employee_id, roster_date) in leave_map:
                        continue

                    eligible.append(
                        (assignment_id, employee_id)
                    )

                daily_tasks.append({
                    "brand_id": brand_id,
                    "process_id": process_id,
                    "required": required_staff,
                    "eligible": eligible
                })

            # Schedule the tasks with fewer eligible
            # employees first to reduce greedy allocation issues.

            daily_tasks.sort(
                key=lambda task: (
                    len(task["eligible"]),
                    -task["required"]
                )
            )

            scheduled_today = set()

            for task in daily_tasks:

                brand_id = task["brand_id"]
                process_id = task["process_id"]
                required = task["required"]

                available = [
                    item for item in task["eligible"]
                    if item[1] not in scheduled_today
                ]

                # Distribute work fairly across the month
                available.sort(
                    key=lambda item: (
                        monthly_employee_load.get(item[1], 0),
                        item[1]
                    )
                )

                selected = available[:required]

                for assignment_id, employee_id in selected:

                    cursor.execute("""
                        INSERT INTO roster_entries
                        (
                            assignment_id,
                            employee_id,
                            brand_id,
                            process_id,
                            roster_date,
                            status
                        )
                        VALUES (?, ?, ?, ?, ?, 'Scheduled')
                    """, (
                        assignment_id,
                        employee_id,
                        brand_id,
                        process_id,
                        roster_date
                    ))

                    scheduled_today.add(employee_id)

                    monthly_employee_load[employee_id] = (
                        monthly_employee_load.get(employee_id, 0) + 1
                    )

                    generated_count += 1

                # Record staffing shortage
                if len(selected) < required:

                    issue = (
                        f"Minimum staffing shortage: "
                        f"required {required}, "
                        f"assigned {len(selected)}."
                    )

                    cursor.execute("""
                        INSERT INTO roster_conflicts
                        (
                            roster_date,
                            brand_id,
                            process_id,
                            required_staff,
                            assigned_staff,
                            issue
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        roster_date,
                        brand_id,
                        process_id,
                        required,
                        len(selected),
                        issue
                    ))

                    conflict_count += 1

            current_date += timedelta(days=1)

        conn.commit()

        return {
            "success": True,
            "message": "Monthly roster generated successfully.",
            "generated": generated_count,
            "conflicts": conflict_count
        }

    except Exception as e:

        conn.rollback()

        return {
            "success": False,
            "message": str(e),
            "generated": 0,
            "conflicts": 0
        }

    finally:
        conn.close()
