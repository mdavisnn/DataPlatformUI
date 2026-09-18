import streamlit as st

from components.header import render_header
from services.page_context import selected_run
from services.profiling_reader import load_profiling
from services.output_reader import load_profiles


settings, run = selected_run()
render_header("Profiling", "The structure, completeness, and characteristics of the data")
data = load_profiling(settings, run.run_id)
profiles = load_profiles(settings, run.run_id)
if not data and not profiles:
    st.info("No profiling metadata is available for this run.")
else:
    if profiles:
        dataset = st.selectbox("Dataset", list(profiles), key="profile_dataset")
        profile = profiles[dataset]
        with st.container(horizontal=True):
            st.metric("Rows", f"{profile.get('row_count', 0):,}", border=True)
            st.metric("Columns", profile.get("column_count", 0), border=True)
        columns = profile.get("columns", [])
        if columns:
            display_columns = [
                {
                    **column,
                    "examples": ", ".join(str(value) for value in column.get("examples", [])),
                }
                for column in columns
                if isinstance(column, dict)
            ]
            st.dataframe(display_columns, hide_index=True, key="profile_columns")
        with st.expander("Raw dataset profile"):
            st.json(profile, expanded=False)
    with st.expander("Profiling stage evidence"):
        st.json(data, expanded=False)
