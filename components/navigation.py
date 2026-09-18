import streamlit as st


def render_navigation() -> None:
    st.page_link("app.py", label="Runs", icon="🏠")
    st.page_link("pages/overview.py", label="Overview")
    st.page_link("pages/discovery.py", label="Discovery")
    st.page_link("pages/profiling.py", label="Profiling")
    st.page_link("pages/processing.py", label="Processing")
    st.page_link("pages/validation.py", label="Validation")
    st.page_link("pages/curation.py", label="Curation")
    st.page_link("pages/analysis.py", label="Analysis")
    st.page_link("pages/summary.py", label="Summary")
