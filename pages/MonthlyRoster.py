
import streamlit as st
import pandas as pd
import calendar
from datetime import date

from database import get_connection
from scheduler import generate_month_roster

st.set_page_config(
    page_title="Roster Generator",
    page_icon="📅",
    layout="wide"
)

st.title("📅 Automatic Monthly Roster Generator")

st.write(
    "Generate monthly employee schedules using "
    "assignments, operating rules and employee availability."
)

conn = get_connection()

# ------------------------------------------
# 1. SELECT MONTH AND YEAR
# ------------------------------------------

today = date.today()

col1, col2 = st.columns(2)

with col1:

    selected_month = st.selectbox(
        "Select Month",
        range(1, 13),
        index=today.month - 1,
        format_func=lambda x: calendar.month_name[x]
    )

with col2:

    selected_year = st.number_input(
        "Select Year",
        min_value=2024,
        max_value=2035,
        value=today.year
    )

start_date = date(
    int(selected_year),
    selected_month,
    1
)

end_date = date(
    int(selected_year),
    selected_month,
    calendar.monthrange(
        int(selected_year),
        selected_month
    )[1]
)

# ------------------------------------------
# 2. EXISTING ROSTER INFORMATION
# ------------------------------------------

existing_count = conn.execute("""
    SELECT COUNT(*)
    FROM roster_entries
    WHERE roster_date BETWEEN ? AND ?
""", (
    start_date.isoformat(),
    end_date.isoformat()
)).fetchone()[0]

existing_conflicts = conn.execute("""
    SELECT COUNT(*)
    FROM roster_conflicts
    WHERE roster_date BETWEEN ? AND ?
""", (
    start_date.isoformat(),
    end_date.isoformat()
)).fetchone()[0]

col1, col2 = st.columns(2)

col1.metric("Existing Roster Entries", existing_count)
col2.metric("Recorded Staffing Conflicts", existing_conflicts)

st.divider()

# ------------------------------------------
# 3. GENERATE ROSTER
# ------------------------------------------

st.header("Generate Monthly Roster")

st.warning(
    "Generating this month again will replace its existing "
    "generated roster entries and recorded staffing conflicts."
)

confirmation = st.checkbox(
    "I understand that existing roster data for this month will be replaced."
)

if st.button(
    "Generate Monthly Roster",
    type="primary",
    disabled=not confirmation
):

    with st.spinner("Generating monthly roster..."):

        result = generate_month_roster(
            int(selected_year),
            selected_month
        )

    if result["success"]:

        st.success(result["message"])

        col1, col2 = st.columns(2)

        col1.metric(
            "Generated Assignments",
            result["generated"]
        )

        col2.metric(
            "Staffing Conflicts",
            result["conflicts"]
        )

    else:

        st.error(result["message"])

st.divider()

# ------------------------------------------
# 4. VIEW GENERATED ROSTER
# ------------------------------------------

st.header("Generated Monthly Roster")

roster = pd.read_sql_query("""
    SELECT
        r.roster_date,
        e.employee_name,
        e.employee_id,
        b.brand_name,
        p.process_name,
        r.status
    FROM roster_entries r
    JOIN employees e
        ON r.employee_id = e.employee_id
    JOIN brands b
        ON r.brand_id = b.brand_id
    JOIN processes p
        ON r.process_id = p.process_id
    WHERE r.roster_date BETWEEN ? AND ?
    ORDER BY
        r.roster_date,
        b.brand_name,
        p.process_name
""", conn, params=(
    start_date.isoformat(),
    end_date.isoformat()
))

if not roster.empty:

    st.dataframe(
        roster,
        use_container_width=True,
        hide_index=True
    )

    st.download_button(
        "Download Roster as CSV",
        data=roster.to_csv(index=False).encode("utf-8"),
        file_name=f"roster_{selected_year}_{selected_month:02d}.csv",
        mime="text/csv"
    )

else:

    st.info(
        "No roster has been generated for this month yet."
    )

st.divider()

# ------------------------------------------
# 5. VIEW STAFFING CONFLICTS
# ------------------------------------------

st.header("Staffing Shortages")

conflicts = pd.read_sql_query("""
    SELECT
        c.roster_date,
        b.brand_name,
        p.process_name,
        c.required_staff,
        c.assigned_staff,
        c.issue
    FROM roster_conflicts c
    JOIN brands b
        ON c.brand_id = b.brand_id
    JOIN processes p
        ON c.process_id = p.process_id
    WHERE c.roster_date BETWEEN ? AND ?
    ORDER BY c.roster_date
""", conn, params=(
    start_date.isoformat(),
    end_date.isoformat()
))

if not conflicts.empty:

    st.error(
        f"{len(conflicts)} staffing shortages found."
    )

    st.dataframe(
        conflicts,
        use_container_width=True,
        hide_index=True
    )

else:

    st.success("No staffing shortages recorded.")



# ------------------------------------------
# 6. MANUAL ROSTER EDITING
# ------------------------------------------

st.divider()
st.header("✏️ Manual Roster Reassignment")

st.write(
    "Replace an assigned employee with another eligible "
    "employee for the same brand and process."
)

edit_roster = pd.read_sql_query("""
    SELECT
        r.roster_id,
        r.assignment_id,
        r.roster_date,
        r.employee_id,
        r.brand_id,
        r.process_id,
        e.employee_name,
        b.brand_name,
        p.process_name
    FROM roster_entries r
    JOIN employees e ON r.employee_id = e.employee_id
    JOIN brands b ON r.brand_id = b.brand_id
    JOIN processes p ON r.process_id = p.process_id
    WHERE r.roster_date BETWEEN ? AND ?
    ORDER BY r.roster_date
""", conn, params=(
    start_date.isoformat(),
    end_date.isoformat()
))

if not edit_roster.empty:

    roster_options = {
        int(row["roster_id"]):
        f'{row["roster_date"]} | {row["employee_name"]} | '
        f'{row["brand_name"]} - {row["process_name"]}'
        for _, row in edit_roster.iterrows()
    }

    selected_id = st.selectbox(
        "Select roster entry to change",
        options=list(roster_options.keys()),
        format_func=lambda x: roster_options[x]
    )

    selected_row = edit_roster[
        edit_roster["roster_id"] == selected_id
    ].iloc[0]

    roster_date = selected_row["roster_date"]
    weekday = date.fromisoformat(roster_date).weekday()

    # Find eligible employees assigned to the same task.
    candidates = pd.read_sql_query("""
        SELECT
            a.assignment_id,
            e.employee_id,
            e.employee_name
        FROM assignments a
        JOIN employees e ON a.employee_id = e.employee_id
        WHERE a.brand_id = ?
          AND a.process_id = ?
          AND e.is_active = 1
          AND e.employee_id != ?

          AND NOT EXISTS (
              SELECT 1
              FROM employee_weekly_offs w
              WHERE w.employee_id = e.employee_id
                AND w.weekday = ?
          )

          AND NOT EXISTS (
              SELECT 1
              FROM leaves l
              WHERE l.employee_id = e.employee_id
                AND l.leave_date = ?
                AND l.status = 'Approved'
          )

          AND NOT EXISTS (
              SELECT 1
              FROM roster_entries r2
              WHERE r2.employee_id = e.employee_id
                AND r2.roster_date = ?
                AND r2.roster_id != ?
          )

        ORDER BY e.employee_name
    """, conn, params=(
        int(selected_row["brand_id"]),
        int(selected_row["process_id"]),
        int(selected_row["employee_id"]),
        weekday,
        roster_date,
        roster_date,
        int(selected_id)
    ))

    st.write(
        f"**Current employee:** {selected_row['employee_name']}"
    )

    st.write(
        f"**Task:** {selected_row['brand_name']} - "
        f"{selected_row['process_name']}"
    )

    if not candidates.empty:

        employee_options = {
            int(row["employee_id"]): row["employee_name"]
            for _, row in candidates.iterrows()
        }

        with st.form("manual_reassignment_form"):

            new_employee_id = st.selectbox(
                "Select replacement employee",
                options=list(employee_options.keys()),
                format_func=lambda x: employee_options[x]
            )

            save_change = st.form_submit_button(
                "Save Roster Change",
                type="primary"
            )

            if save_change:

                new_assignment_id = int(
                    candidates.loc[
                        candidates["employee_id"] == new_employee_id,
                        "assignment_id"
                    ].iloc[0]
                )

                try:
                    conn.execute("""
                        UPDATE roster_entries
                        SET assignment_id = ?,
                            employee_id = ?
                        WHERE roster_id = ?
                    """, (
                        new_assignment_id,
                        new_employee_id,
                        int(selected_id)
                    ))

                    conn.commit()

                    st.success(
                        "Roster successfully updated!"
                    )

                    st.rerun()

                except Exception as error:

                    conn.rollback()

                    st.error(
                        f"Unable to update roster: {error}"
                    )

    else:

        st.warning(
            "No eligible replacement employee is available "
            "for this brand, process and date."
        )

else:

    st.info(
        "Generate a monthly roster before making manual changes."
    )

conn.close()