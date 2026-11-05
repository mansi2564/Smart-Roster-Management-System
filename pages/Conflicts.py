
import streamlit as st
import pandas as pd
import calendar
from datetime import date
from validator import validate_month_roster

st.set_page_config(
    page_title="Roster Conflict Detection",
    page_icon="⚠️",
    layout="wide"
)

st.title("⚠️ Roster Conflict Detection")
st.write(
    "Validate the generated monthly roster and identify "
    "scheduling errors and staffing shortages."
)

st.divider()

# Select month and year
today = date.today()

col1, col2 = st.columns(2)

with col1:
    month = st.selectbox(
        "Select Month",
        range(1, 13),
        index=today.month - 1,
        format_func=lambda x: calendar.month_name[x]
    )

with col2:
    year = st.number_input(
        "Select Year",
        min_value=2024,
        max_value=2035,
        value=today.year,
        step=1
    )

st.divider()

# Run validation
if st.button("Run Conflict Detection", type="primary"):

    with st.spinner("Validating roster..."):

        conflicts = validate_month_roster(
            int(year),
            int(month)
        )

    st.session_state["validation_conflicts"] = conflicts
    st.session_state["validation_month"] = month
    st.session_state["validation_year"] = year

# Display results
if "validation_conflicts" in st.session_state:

    if (
        st.session_state["validation_month"] == month
        and st.session_state["validation_year"] == year
    ):

        conflicts = st.session_state["validation_conflicts"]

        st.subheader("Validation Results")

        if conflicts:

            df = pd.DataFrame(conflicts)

            total = len(df)
            shortage = sum(
                df["Issue"].str.contains(
                    "Staffing Shortage",
                    case=False,
                    na=False
                )
            )
            other_issues = total - shortage

            c1, c2, c3 = st.columns(3)

            c1.metric("Total Issues", total)
            c2.metric("Staffing Shortages", int(shortage))
            c3.metric("Other Violations", int(other_issues))

            st.error(f"{total} scheduling issues detected.")

            # Issue summary
            st.subheader("Conflict Summary")

            summary = (
                df.groupby("Issue")
                .size()
                .reset_index(name="Count")
                .sort_values("Count", ascending=False)
            )

            st.dataframe(
                summary,
                use_container_width=True,
                hide_index=True
            )

            # Filters
            st.subheader("Detailed Conflict Report")

            issue_types = ["All"] + sorted(
                df["Issue"].dropna().unique().tolist()
            )

            selected_issue = st.selectbox(
                "Filter by Conflict Type",
                issue_types
            )

            if selected_issue != "All":
                filtered_df = df[
                    df["Issue"] == selected_issue
                ]
            else:
                filtered_df = df

            st.dataframe(
                filtered_df,
                use_container_width=True,
                hide_index=True
            )

            # Download report
            st.download_button(
                "Download Conflict Report",
                data=filtered_df.to_csv(index=False).encode("utf-8"),
                file_name=f"conflict_report_{year}_{month:02d}.csv",
                mime="text/csv"
            )

        else:

            st.success(
                "Excellent! No scheduling conflicts found "
                "in the selected monthly roster."
            )

            st.balloons()

        st.caption(
            "Checks include employee double booking, weekly offs, "
            "approved leaves, holidays, operating days, "
            "minimum staffing and duplicate assignments."
        )
