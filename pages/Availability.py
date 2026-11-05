
import streamlit as st
import pandas as pd
from database import get_connection

st.set_page_config(
    page_title="Availability Management",
    page_icon="📅",
    layout="wide"
)

st.title("📅 Availability Management")
st.write(
    "Manage employee availability, weekly offs, leaves, "
    "compensatory offs and company holidays."
)

conn = get_connection()

# -------------------------------------------------
# FETCH EMPLOYEE DATA
# -------------------------------------------------

employees = pd.read_sql_query("""
    SELECT employee_id, employee_name
    FROM employees
    WHERE is_active = 1
    ORDER BY employee_name
""", conn)

employee_options = {
    f"{row.employee_name} (ID: {row.employee_id})": row.employee_id
    for row in employees.itertuples()
}

employee_labels = list(employee_options.keys())

days = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6
}

day_names = {v: k for k, v in days.items()}

# -------------------------------------------------
# DASHBOARD METRICS
# -------------------------------------------------

weekly_offs = pd.read_sql_query(
    "SELECT * FROM employee_weekly_offs", conn
)

leaves = pd.read_sql_query(
    "SELECT * FROM leaves", conn
)

holidays = pd.read_sql_query(
    "SELECT * FROM holidays", conn
)

col1, col2, col3, col4 = st.columns(4)

col1.metric("Weekly Off Records", len(weekly_offs))
col2.metric("Total Leave Records", len(leaves))
col3.metric(
    "Approved Leaves",
    int((leaves["status"] == "Approved").sum())
)
col4.metric("Company Holidays", len(holidays))

st.divider()

# -------------------------------------------------
# TABS
# -------------------------------------------------

tab1, tab2, tab3 = st.tabs([
    "Weekly Offs",
    "Leaves & Comp-Offs",
    "Company Holidays"
])

# =================================================
# TAB 1: WEEKLY OFFS
# =================================================

with tab1:

    st.header("Employee Weekly Offs")

    st.write(
        "Set the regular weekly off day for each employee."
    )

    if not weekly_offs.empty:

        weekly_display = weekly_offs.merge(
            employees,
            on="employee_id",
            how="left"
        )

        # Include inactive employees in historical records
        all_employees = pd.read_sql_query("""
            SELECT employee_id, employee_name
            FROM employees
        """, conn)

        weekly_display = weekly_offs.merge(
            all_employees,
            on="employee_id",
            how="left"
        )

        weekly_display["Weekday"] = weekly_display[
            "weekday"
        ].map(day_names)

        weekly_display = weekly_display.rename(columns={
            "employee_name": "Employee",
            "employee_id": "Employee ID"
        })

        st.dataframe(
            weekly_display[
                ["Employee ID", "Employee", "Weekday"]
            ],
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info("No weekly offs have been configured.")

    st.subheader("➕ Add Weekly Off")

    if not employees.empty:

        with st.form("weekly_off_form"):

            selected_employee = st.selectbox(
                "Select Employee",
                employee_labels,
                key="weekly_employee"
            )

            selected_day = st.selectbox(
                "Select Weekly Off Day",
                list(days.keys())
            )

            submitted = st.form_submit_button(
                "Save Weekly Off"
            )

            if submitted:

                employee_id = employee_options[
                    selected_employee
                ]

                weekday = days[selected_day]

                existing = conn.execute("""
                    SELECT id
                    FROM employee_weekly_offs
                    WHERE employee_id = ?
                    AND weekday = ?
                """, (employee_id, weekday)).fetchone()

                if existing:

                    st.warning(
                        "This weekly off is already configured."
                    )

                else:

                    conn.execute("""
                        INSERT INTO employee_weekly_offs
                        (employee_id, weekday)
                        VALUES (?, ?)
                    """, (employee_id, weekday))

                    conn.commit()

                    st.success("Weekly off saved successfully!")
                    st.rerun()

    else:
        st.warning("No active employees available.")

    st.divider()

    st.subheader("Remove Weekly Off")

    if not weekly_offs.empty:

        all_employees = pd.read_sql_query("""
            SELECT employee_id, employee_name
            FROM employees
        """, conn)

        weekly_options = {}

        for row in weekly_offs.itertuples():

            employee_name = all_employees.loc[
                all_employees["employee_id"] == row.employee_id,
                "employee_name"
            ].iloc[0]

            label = (
                f"{employee_name} - "
                f"{day_names[row.weekday]}"
            )

            weekly_options[label] = row.id

        selected_off = st.selectbox(
            "Select Weekly Off to Remove",
            list(weekly_options.keys())
        )

        if st.button("Remove Weekly Off"):

            conn.execute("""
                DELETE FROM employee_weekly_offs
                WHERE id = ?
            """, (weekly_options[selected_off],))

            conn.commit()

            st.success("Weekly off removed successfully!")
            st.rerun()


# =================================================
# TAB 2: LEAVES AND COMP-OFFS
# =================================================

with tab2:

    st.header("Employee Leaves & Comp-Offs")

    st.write(
        "Record employee leave requests and compensatory offs. "
        "Only approved records will block roster scheduling."
    )

    if not leaves.empty:

        all_employees = pd.read_sql_query("""
            SELECT employee_id, employee_name
            FROM employees
        """, conn)

        leave_display = leaves.merge(
            all_employees,
            on="employee_id",
            how="left"
        )

        leave_display = leave_display.rename(columns={
            "employee_name": "Employee",
            "leave_date": "Date",
            "leave_type": "Leave Type",
            "status": "Approval Status"
        })

        st.dataframe(
            leave_display[
                [
                    "Employee",
                    "Date",
                    "Leave Type",
                    "Approval Status"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info("No leave records available.")

    st.subheader("➕ Add Leave / Comp-Off")

    if not employees.empty:

        with st.form("leave_form"):

            selected_employee = st.selectbox(
                "Select Employee",
                employee_labels,
                key="leave_employee"
            )

            leave_date = st.date_input(
                "Select Date"
            )

            leave_type = st.selectbox(
                "Leave Type",
                [
                    "Planned Leave",
                    "Sick Leave",
                    "Emergency Leave",
                    "Comp-Off"
                ]
            )

            status = st.selectbox(
                "Approval Status",
                [
                    "Pending",
                    "Approved",
                    "Rejected"
                ]
            )

            submitted = st.form_submit_button(
                "Save Leave Record"
            )

            if submitted:

                employee_id = employee_options[
                    selected_employee
                ]

                conn.execute("""
                    INSERT INTO leaves
                    (employee_id, leave_date, leave_type, status)
                    VALUES (?, ?, ?, ?)

                    ON CONFLICT(employee_id, leave_date)
                    DO UPDATE SET
                        leave_type = excluded.leave_type,
                        status = excluded.status
                """, (
                    employee_id,
                    leave_date.isoformat(),
                    leave_type,
                    status
                ))

                conn.commit()

                st.success("Leave record saved successfully!")
                st.rerun()

    else:
        st.warning("No active employees available.")

    st.divider()

    st.subheader("Update Leave Approval")

    if not leaves.empty:

        all_employees = pd.read_sql_query("""
            SELECT employee_id, employee_name
            FROM employees
        """, conn)

        leave_options = {}

        for row in leaves.itertuples():

            employee_name = all_employees.loc[
                all_employees["employee_id"] == row.employee_id,
                "employee_name"
            ].iloc[0]

            label = (
                f"{employee_name} | {row.leave_date} | "
                f"{row.leave_type} | {row.status}"
            )

            leave_options[label] = row.leave_id

        selected_leave = st.selectbox(
            "Select Leave Record",
            list(leave_options.keys())
        )

        new_status = st.selectbox(
            "New Approval Status",
            ["Pending", "Approved", "Rejected"],
            key="new_leave_status"
        )

        if st.button("Update Leave Status"):

            conn.execute("""
                UPDATE leaves
                SET status = ?
                WHERE leave_id = ?
            """, (
                new_status,
                leave_options[selected_leave]
            ))

            conn.commit()

            st.success("Leave status updated successfully!")
            st.rerun()


# =================================================
# TAB 3: COMPANY HOLIDAYS
# =================================================

with tab3:

    st.header("Company Holidays")

    st.write(
        "Manage holidays that apply to the entire organization."
    )

    if not holidays.empty:

        st.dataframe(
            holidays.rename(columns={
                "holiday_date": "Holiday Date",
                "holiday_name": "Holiday Name"
            }),
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info("No company holidays configured.")

    st.subheader("➕ Add Company Holiday")

    with st.form("holiday_form"):

        holiday_name = st.text_input(
            "Holiday Name"
        )

        holiday_date = st.date_input(
            "Holiday Date",
            key="holiday_date"
        )

        submitted = st.form_submit_button(
            "Add Holiday"
        )

        if submitted:

            if not holiday_name.strip():

                st.error("Please enter a holiday name.")

            else:

                existing = conn.execute("""
                    SELECT holiday_id
                    FROM holidays
                    WHERE holiday_date = ?
                """, (holiday_date.isoformat(),)).fetchone()

                if existing:

                    st.warning(
                        "A holiday already exists on this date."
                    )

                else:

                    conn.execute("""
                        INSERT INTO holidays
                        (holiday_date, holiday_name)
                        VALUES (?, ?)
                    """, (
                        holiday_date.isoformat(),
                        holiday_name.strip()
                    ))

                    conn.commit()

                    st.success("Company holiday added successfully!")
                    st.rerun()

    st.divider()

    st.subheader("Remove Company Holiday")

    if not holidays.empty:

        holiday_options = {
            f"{row.holiday_name} - {row.holiday_date}":
            row.holiday_id
            for row in holidays.itertuples()
        }

        selected_holiday = st.selectbox(
            "Select Holiday",
            list(holiday_options.keys())
        )

        if st.button("Remove Holiday"):

            conn.execute("""
                DELETE FROM holidays
                WHERE holiday_id = ?
            """, (holiday_options[selected_holiday],))

            conn.commit()

            st.success("Holiday removed successfully!")
            st.rerun()

conn.close()
