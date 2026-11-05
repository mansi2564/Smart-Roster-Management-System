
import streamlit as st
import pandas as pd
from database import get_connection

st.set_page_config(
    page_title="Employee Management",
    page_icon="👥",
    layout="wide"
)

st.title("👥 Employee Management")
st.write("Manage employees, their roles and operational pods.")

conn = get_connection()

# Fetch employee details
employees = pd.read_sql_query("""
    SELECT
        e.employee_id,
        e.employee_name,
        e.email,
        p.pod_name,
        e.role,
        e.is_active
    FROM employees e
    LEFT JOIN pods p ON e.pod_id = p.pod_id
    ORDER BY e.employee_id
""", conn)

# Dashboard metrics
col1, col2, col3 = st.columns(3)

col1.metric("Total Employees", len(employees))
col2.metric("Active Employees", int((employees["is_active"] == 1).sum()))
col3.metric("Inactive Employees", int((employees["is_active"] == 0).sum()))

st.divider()

# Search and filters
st.subheader("Employee Directory")

search = st.text_input("Search by employee name or email")

pod_options = ["All"] + sorted(
    employees["pod_name"].dropna().unique().tolist()
)

selected_pod = st.selectbox("Filter by Pod", pod_options)

role_options = ["All"] + sorted(
    employees["role"].dropna().unique().tolist()
)

selected_role = st.selectbox("Filter by Role", role_options)

filtered = employees.copy()

if search:
    filtered = filtered[
        filtered["employee_name"].str.contains(search, case=False, na=False)
        | filtered["email"].str.contains(search, case=False, na=False)
    ]

if selected_pod != "All":
    filtered = filtered[filtered["pod_name"] == selected_pod]

if selected_role != "All":
    filtered = filtered[filtered["role"] == selected_role]

st.dataframe(
    filtered,
    use_container_width=True,
    hide_index=True
)

st.caption(f"Showing {len(filtered)} employees")

st.divider()

# Add employee
st.subheader("➕ Add New Employee")

pods = pd.read_sql_query(
    "SELECT pod_id, pod_name FROM pods ORDER BY pod_name",
    conn
)

with st.form("add_employee_form"):
    name = st.text_input("Employee Name")
    email = st.text_input("Email Address")

    pod_name = st.selectbox("Select Pod", pods["pod_name"].tolist())

    role = st.selectbox(
        "Select Role",
        ["Employee", "Pod Lead"]
    )

    submitted = st.form_submit_button("Add Employee")

    if submitted:
        if not name.strip() or not email.strip():
            st.error("Please enter both name and email.")

        elif "@" not in email or "." not in email.split("@")[-1]:
            st.error("Please enter a valid email address.")

        else:
            pod_id = int(
                pods.loc[pods["pod_name"] == pod_name, "pod_id"].iloc[0]
            )

            try:
                conn.execute("""
                    INSERT INTO employees
                    (employee_name, email, pod_id, role, is_active)
                    VALUES (?, ?, ?, ?, 1)
                """, (name.strip(), email.strip(), pod_id, role))

                conn.commit()
                st.success("Employee added successfully!")
                st.rerun()

            except Exception as e:
                st.error(f"Unable to add employee: {e}")

st.divider()

# Deactivate employee
st.subheader("Deactivate Employee")

active_employees = employees[employees["is_active"] == 1]

if not active_employees.empty:
    employee_options = {
        f'{row.employee_name} (ID: {row.employee_id})': row.employee_id
        for row in active_employees.itertuples()
    }

    selected_employee = st.selectbox(
        "Select Employee",
        list(employee_options.keys())
    )

    if st.button("Deactivate Employee", type="secondary"):
        employee_id = employee_options[selected_employee]

        conn.execute("""
            UPDATE employees
            SET is_active = 0
            WHERE employee_id = ?
        """, (employee_id,))

        conn.commit()
        st.success("Employee deactivated successfully!")
        st.rerun()
else:
    st.info("No active employees available.")

conn.close()
