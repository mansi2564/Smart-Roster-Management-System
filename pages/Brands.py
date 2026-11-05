
import streamlit as st
import pandas as pd
import json
from database import get_connection

st.set_page_config(
    page_title="Brand & Process Management",
    page_icon="🏢",
    layout="wide"
)

st.title("🏢 Brand & Process Management")
st.write("Manage brands, processes and their operational requirements.")

conn = get_connection()

# -------------------------------------------------
# 1. DASHBOARD METRICS
# -------------------------------------------------

brands = pd.read_sql_query("""
    SELECT * FROM brands
    ORDER BY brand_name
""", conn)

processes = pd.read_sql_query("""
    SELECT * FROM processes
    ORDER BY process_name
""", conn)

rules = pd.read_sql_query("""
    SELECT * FROM brand_process_rules
""", conn)

col1, col2, col3 = st.columns(3)

col1.metric("Total Brands", len(brands))
col2.metric("Total Processes", len(processes))
col3.metric("Configured Brand-Process Rules", len(rules))

st.divider()

# -------------------------------------------------
# 2. BRAND DIRECTORY
# -------------------------------------------------

st.header("Brand Directory")

st.dataframe(
    brands,
    use_container_width=True,
    hide_index=True
)

with st.expander("➕ Add New Brand"):

    with st.form("add_brand_form"):

        brand_name = st.text_input("Brand Name")
        description = st.text_area("Brand Description")

        submitted = st.form_submit_button("Add Brand")

        if submitted:

            if not brand_name.strip():
                st.error("Please enter a brand name.")

            else:
                existing = conn.execute("""
                    SELECT brand_id FROM brands
                    WHERE LOWER(brand_name) = LOWER(?)
                """, (brand_name.strip(),)).fetchone()

                if existing:
                    st.warning("This brand already exists. Please enter a different name.")

                else:
                    conn.execute("""
                        INSERT INTO brands
                        (brand_name, description, is_active)
                        VALUES (?, ?, 1)
                    """, (brand_name.strip(), description.strip()))

                    conn.commit()
                    st.success("Brand added successfully!")
                    st.rerun()

st.divider()

# -------------------------------------------------
# 3. PROCESS MANAGEMENT
# -------------------------------------------------

st.header("Process Management")

st.dataframe(
    processes,
    use_container_width=True,
    hide_index=True
)

with st.expander("➕ Add New Process"):

    with st.form("add_process_form"):

        process_name = st.text_input("Process Name")

        submitted = st.form_submit_button("Add Process")

        if submitted:

            if not process_name.strip():
                st.error("Please enter a process name.")

            else:
                try:
                    conn.execute("""
                        INSERT INTO processes (process_name)
                        VALUES (?)
                    """, (process_name.strip(),))

                    conn.commit()
                    st.success("Process added successfully!")
                    st.rerun()

                except Exception as e:
                    st.error(f"Unable to add process: {e}")

st.divider()

# -------------------------------------------------
# 4. BRAND-PROCESS CONFIGURATION
# -------------------------------------------------

st.header("Brand-Process Configuration")

st.write(
    "Select which processes operate under each brand, "
    "along with operating days and minimum staffing."
)

brands = pd.read_sql_query("""
    SELECT brand_id, brand_name
    FROM brands
    WHERE is_active = 1
    ORDER BY brand_name
""", conn)

processes = pd.read_sql_query("""
    SELECT process_id, process_name
    FROM processes
    ORDER BY process_name
""", conn)

days = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6
}

if not brands.empty and not processes.empty:

    with st.form("brand_process_form"):

        selected_brand = st.selectbox(
            "Select Brand",
            brands["brand_name"].tolist()
        )

        selected_process = st.selectbox(
            "Select Process",
            processes["process_name"].tolist()
        )

        selected_days = st.multiselect(
            "Operating Days",
            list(days.keys()),
            default=list(days.keys())
        )

        min_staffing = st.number_input(
            "Minimum Required Employees",
            min_value=1,
            max_value=50,
            value=1
        )

        
        # Public holiday operating policy

        holiday_policy = st.selectbox(
            "Public Holiday Policy",
            ["OFF", "WORK"],
            format_func=lambda x: (
                "Works on Public Holidays" if x == "WORK"
                else "Public Holidays Off"
            )
        )

        # Optional weekday staffing overrides

        daily_staffing = {}

        with st.expander("Configure Different Staffing by Day"):

            st.caption(
                "Enter 0 to use the default minimum staffing requirement."
            )

            for day_name, weekday_number in days.items():

                override = st.number_input(
                    f"{day_name} Minimum Staffing (0 = Default)",
                    min_value=0,
                    max_value=50,
                    value=0,
                    key=f"staff_override_{weekday_number}"
                )

                if override > 0:
                    daily_staffing[str(weekday_number)] = int(override)


        submitted = st.form_submit_button(
            "Save Brand-Process Configuration"
        )

        if submitted:

            if not selected_days:
                st.error("Select at least one operating day.")

            else:

                brand_id = int(
                    brands.loc[
                        brands["brand_name"] == selected_brand,
                        "brand_id"
                    ].iloc[0]
                )

                process_id = int(
                    processes.loc[
                        processes["process_name"] == selected_process,
                        "process_id"
                    ].iloc[0]
                )

                operating_days = [
                    days[day] for day in selected_days
                ]

                try:
                    conn.execute("""
                        INSERT INTO brand_process_rules
                        (brand_id, process_id, operating_days, min_staffing, holiday_policy, daily_staffing)
                        VALUES (?, ?, ?, ?, ?, ?)

                        ON CONFLICT(brand_id, process_id)
                        DO UPDATE SET
                            operating_days = excluded.operating_days,
                            min_staffing = excluded.min_staffing,
                            holiday_policy = excluded.holiday_policy,
                            daily_staffing = excluded.daily_staffing
                    """, (
                        brand_id,
                        process_id,
                        json.dumps(operating_days),
                        min_staffing,
                        holiday_policy,
                        json.dumps(daily_staffing)
                    ))

                    conn.commit()
                    st.success("Configuration saved successfully!")
                    st.rerun()

                except Exception as e:
                    st.error(f"Unable to save configuration: {e}")

else:
    st.warning("Please add at least one brand and one process first.")

st.divider()

# -------------------------------------------------
# 5. VIEW CONFIGURED RULES
# -------------------------------------------------

st.header("Configured Brand-Process Rules")

configured_rules = pd.read_sql_query("""
    SELECT
        b.brand_name,
        p.process_name,
        r.operating_days,
        r.min_staffing
    FROM brand_process_rules r
    JOIN brands b ON r.brand_id = b.brand_id
    JOIN processes p ON r.process_id = p.process_id
    ORDER BY b.brand_name, p.process_name
""", conn)

if not configured_rules.empty:

    day_names = {
        0: "Monday",
        1: "Tuesday",
        2: "Wednesday",
        3: "Thursday",
        4: "Friday",
        5: "Saturday",
        6: "Sunday"
    }

    configured_rules["Operating Days"] = configured_rules[
        "operating_days"
    ].apply(
        lambda value: ", ".join(
            day_names[d] for d in json.loads(value)
        )
    )

    configured_rules = configured_rules.rename(columns={
        "brand_name": "Brand",
        "process_name": "Process",
        "min_staffing": "Minimum Staffing"
    })

    configured_rules = configured_rules.drop(
        columns=["operating_days"]
    )

    st.dataframe(
        configured_rules,
        use_container_width=True,
        hide_index=True
    )

else:
    st.info("No brand-process configurations found.")

conn.close()
