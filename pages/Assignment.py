
import streamlit as st
import pandas as pd
from database import get_connection

st.set_page_config(
    page_title="Assignment Management",
    page_icon="📋",
    layout="wide"
)

st.title("📋 Assignment Management")
st.write(
    "Assign employees to brands and their respective processes."
)

conn = get_connection()

# -------------------------------------------------
# 1. FETCH ASSIGNMENT DATA
# -------------------------------------------------

def get_assignments():

    return pd.read_sql_query("""
        SELECT
            a.assignment_id,
            e.employee_id,
            e.employee_name,
            e.role,
            p.pod_name,
            b.brand_name,
            pr.process_name
        FROM assignments a
        JOIN employees e
            ON a.employee_id = e.employee_id
        JOIN brands b
            ON a.brand_id = b.brand_id
        JOIN processes pr
            ON a.process_id = pr.process_id
        LEFT JOIN pods p
            ON e.pod_id = p.pod_id
        ORDER BY b.brand_name, pr.process_name, e.employee_name
    """, conn)


assignments = get_assignments()

# -------------------------------------------------
# 2. DASHBOARD METRICS
# -------------------------------------------------

col1, col2, col3 = st.columns(3)

col1.metric("Total Assignments", len(assignments))

col2.metric(
    "Assigned Employees",
    assignments["employee_id"].nunique()
)

col3.metric(
    "Brands Covered",
    assignments["brand_name"].nunique()
)

st.divider()

# -------------------------------------------------
# 3. VIEW ASSIGNMENTS
# -------------------------------------------------

st.header("Employee Assignment Directory")

if not assignments.empty:

    st.dataframe(
        assignments.drop(columns=["assignment_id"]),
        use_container_width=True,
        hide_index=True
    )

else:
    st.info("No employee assignments found.")

st.divider()

# -------------------------------------------------
# 4. ADD NEW ASSIGNMENT
# -------------------------------------------------

st.header("➕ Assign Employee")

active_employees = pd.read_sql_query("""
    SELECT employee_id, employee_name, role
    FROM employees
    WHERE is_active = 1
    ORDER BY employee_name
""", conn)

active_brands = pd.read_sql_query("""
    SELECT brand_id, brand_name
    FROM brands
    WHERE is_active = 1
    ORDER BY brand_name
""", conn)

if active_employees.empty or active_brands.empty:

    st.warning("You need at least one active employee and brand.")

else:

    with st.form("assignment_form"):

        selected_employee = st.selectbox(
            "Select Employee",
            active_employees["employee_id"].tolist(),
            format_func=lambda x: (
                active_employees.loc[
                    active_employees["employee_id"] == x,
                    "employee_name"
                ].iloc[0]
                + f" (ID: {x})"
            )
        )

        selected_brand = st.selectbox(
            "Select Brand",
            active_brands["brand_id"].tolist(),
            format_func=lambda x: active_brands.loc[
                active_brands["brand_id"] == x,
                "brand_name"
            ].iloc[0]
        )

        # Fetch processes configured for the selected brand
        available_processes = pd.read_sql_query("""
            SELECT
                p.process_id,
                p.process_name
            FROM brand_process_rules r
            JOIN processes p
                ON r.process_id = p.process_id
            WHERE r.brand_id = ?
            ORDER BY p.process_name
        """, conn, params=(int(selected_brand),))

        if not available_processes.empty:

            selected_process = st.selectbox(
                "Select Process",
                available_processes["process_id"].tolist(),
                format_func=lambda x: available_processes.loc[
                    available_processes["process_id"] == x,
                    "process_name"
                ].iloc[0]
            )

        else:
            selected_process = None
            st.warning(
                "This brand has no configured processes. "
                "Configure a process first in Brand & Process Management."
            )

        submitted = st.form_submit_button("Assign Employee")

        if submitted:

            if selected_process is None:

                st.error("Please configure a process for this brand first.")

            else:

                try:

                    conn.execute("""
                        INSERT INTO assignments
                        (employee_id, brand_id, process_id)
                        VALUES (?, ?, ?)
                    """, (
                        int(selected_employee),
                        int(selected_brand),
                        int(selected_process)
                    ))

                    conn.commit()

                    st.success("Employee assigned successfully!")
                    st.rerun()

                except Exception as e:

                    if "UNIQUE constraint failed" in str(e):
                        st.warning(
                            "This employee is already assigned "
                            "to this brand and process."
                        )
                    else:
                        st.error(f"Assignment failed: {e}")

st.divider()

# -------------------------------------------------
# 5. FILTER ASSIGNMENTS
# -------------------------------------------------

st.header("Filter Assignments")

if not assignments.empty:

    brand_filter = st.selectbox(
        "Filter by Brand",
        ["All"] + sorted(assignments["brand_name"].unique().tolist())
    )

    process_filter = st.selectbox(
        "Filter by Process",
        ["All"] + sorted(assignments["process_name"].unique().tolist())
    )

    filtered = assignments.copy()

    if brand_filter != "All":
        filtered = filtered[
            filtered["brand_name"] == brand_filter
        ]

    if process_filter != "All":
        filtered = filtered[
            filtered["process_name"] == process_filter
        ]

    st.dataframe(
        filtered.drop(columns=["assignment_id"]),
        use_container_width=True,
        hide_index=True
    )

    st.caption(f"Showing {len(filtered)} assignments")

st.divider()

# -------------------------------------------------
# 6. REMOVE ASSIGNMENT
# -------------------------------------------------

st.header("Remove Employee Assignment")

if not assignments.empty:

    assignment_options = {
        (
            f'{row.employee_name} | '
            f'{row.brand_name} | '
            f'{row.process_name} '
            f'(ID: {row.assignment_id})'
        ): row.assignment_id
        for row in assignments.itertuples()
    }

    selected_assignment = st.selectbox(
        "Select Assignment to Remove",
        list(assignment_options.keys())
    )

    if st.button("Remove Assignment", type="secondary"):

        assignment_id = assignment_options[selected_assignment]

        roster_count = conn.execute("""
            SELECT COUNT(*)
            FROM roster_entries
            WHERE assignment_id = ?
        """, (int(assignment_id),)).fetchone()[0]

        if roster_count > 0:

            st.error(
                "This assignment is already used in roster entries. "
                "It cannot be removed until those roster entries "
                "are handled."
            )

        else:

            conn.execute("""
                DELETE FROM assignments
                WHERE assignment_id = ?
            """, (int(assignment_id),))

            conn.commit()

            st.success("Assignment removed successfully!")
            st.rerun()

else:

    st.info("There are no assignments to remove.")

conn.close()
