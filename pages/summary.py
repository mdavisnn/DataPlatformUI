import streamlit as st

from components.header import render_header
from services.page_context import selected_run


settings, run = selected_run()
render_header("Summary", "A concise, explainable assessment of data readiness")
if run.status in {"success", "completed"}:
    st.success("The governed pipeline completed successfully for this run.")
else:
    detail = f" at {run.failed_stage}" if run.failed_stage else ""
    st.warning(f"This run requires attention{detail}. Review the detailed evidence before proceeding.")
st.caption("Rule-based headline findings will be added as the metadata mapping is refined.")

