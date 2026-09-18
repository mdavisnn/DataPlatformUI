import streamlit as st

from components.header import render_header
from services.discovery_reader import load_discovery
from services.page_context import selected_run


settings, run = selected_run()
render_header("Discovery", "What arrived, what was recognised, and what may need attention")
data = load_discovery(settings, run.run_id)
if data:
    st.json(data, expanded=False)
else:
    st.info("No discovery or source inventory metadata is available for this run.")

