
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from calendar import month_name
from database import get_connection

st.set_page_config(
    page_title="Smart Roster Management System",
    page_icon="📅",
    layout="wide"
)

# Database connection
conn = get_connection()

today = date.today()
month_start = today.replace(day=1).isoformat()

if today.month == 12:
    next_month = date(today.year + 1, 1, 1).isoformat()
else:
    next_month = date(today.year, today.month + 1, 1).isoformat()

# Dashboard title
st.title("📅 Smart Roster Management System")
st.write(
    f"Welcome to your workforce scheduling dashboard | "
    f"{month_name[today.month]} {today.year}"
)

st.divider()

# Fetch dashboard statistics
active_employees = pd.read_sql_query(
    "SELECT COUNT(*) AS total FROM employees WHERE is_active = 1",
    conn
).iloc[0]["total"]

total_pods = pd.read_sql_query(
    "SELECT COUNT(*) AS total FROM pods",
    conn
).iloc[0]["total"]

total_brands = pd.read_sql_query(
    "SELECT COUNT(*) AS total FROM brands WHERE is_active = 1",
    conn
).iloc[0]["total"]

total_processes = pd.read_sql_query(
    "SELECT COUNT(*) AS total FROM processes",
    conn
).iloc[0]["total"]

total_assignments = pd.read_sql_query(
    "SELECT COUNT(*) AS total FROM assignments",
    conn
).iloc[0]["total"]

monthly_roster = pd.read_sql_query(
    """
    SELECT COUNT(*) AS total
    FROM roster_entries
    WHERE roster_date >= ? AND roster_date < ?
    """,
    conn,
    params=(month_start, next_month)
).iloc[0]["total"]

monthly_conflicts = pd.read_sql_query(
    """
    SELECT COUNT(*) AS total
    FROM roster_conflicts
    WHERE roster_date >= ? AND roster_date < ?
    """,
    conn,
    params=(month_start, next_month)
).iloc[0]["total"]

# Metric cards
st.subheader("Workforce Overview")

c1, c2, c3, c4 = st.columns(4)

c1.metric("Active Employees", int(active_employees))
c2.metric("Total Pods", int(total_pods))
c3.metric("Active Brands", int(total_brands))
c4.metric("Processes", int(total_processes))

c5, c6, c7 = st.columns(3)

c5.metric("Employee Assignments", int(total_assignments))
c6.metric("Monthly Roster Entries", int(monthly_roster))
c7.metric("Scheduling Conflicts", int(monthly_conflicts))

st.divider()

# Roster charts
st.subheader("Roster Analytics")

roster_by_brand = pd.read_sql_query(
    """
    SELECT b.brand_name, COUNT(r.roster_id) AS total_shifts
    FROM roster_entries r
    JOIN brands b ON r.brand_id = b.brand_id
    WHERE r.roster_date >= ? AND r.roster_date < ?
    GROUP BY b.brand_name
    ORDER BY total_shifts DESC
    """,
    conn,
    params=(month_start, next_month)
)

daily_roster = pd.read_sql_query(
    """
    SELECT roster_date, COUNT(*) AS total_employees
    FROM roster_entries
    WHERE roster_date >= ? AND roster_date < ?
    GROUP BY roster_date
    ORDER BY roster_date
    """,
    conn,
    params=(month_start, next_month)
)

left, right = st.columns(2)

with left:
    st.write("**Employee Shifts by Brand**")

    if not roster_by_brand.empty:
        fig = px.bar(
            roster_by_brand,
            x="brand_name",
            y="total_shifts",
            labels={
                "brand_name": "Brand",
                "total_shifts": "Total Shifts"
            }
        )
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No roster data available for this month.")

with right:
    st.write("**Daily Workforce Allocation**")

    if not daily_roster.empty:
        fig = px.line(
            daily_roster,
            x="roster_date",
            y="total_employees",
            markers=True,
            labels={
                "roster_date": "Date",
                "total_employees": "Employees Scheduled"
            }
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Generate a roster to view daily allocation.")

st.divider()

# Recent roster entries
st.subheader("Recent Roster Entries")

recent_roster = pd.read_sql_query(
    """
    SELECT
        r.roster_date AS Date,
        e.employee_name AS Employee,
        b.brand_name AS Brand,
        p.process_name AS Process,
        r.status AS Status
    FROM roster_entries r
    JOIN employees e ON r.employee_id = e.employee_id
    JOIN brands b ON r.brand_id = b.brand_id
    JOIN processes p ON r.process_id = p.process_id
    WHERE r.roster_date >= ? AND r.roster_date < ?
    ORDER BY r.roster_date DESC
    LIMIT 15
    """,
    conn,
    params=(month_start, next_month)
)

if not recent_roster.empty:
    st.dataframe(recent_roster, use_container_width=True)

    st.download_button(
        "Download Monthly Roster",
        data=recent_roster.to_csv(index=False),
        file_name="monthly_roster.csv",
        mime="text/csv"
    )
else:
    st.info("No roster entries found for the current month.")

conn.close()

st.divider()

st.caption(
    "Smart Roster Management System | "
    "Automated Workforce Scheduling and Conflict Detection"
)
