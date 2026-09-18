import streamlit as st

from config.settings import Settings
from models.run import PipelineRun
from services.run_reader import load_run


def selected_run() -> tuple[Settings, PipelineRun]:
    settings = Settings.from_environment()
    run_id = st.session_state.get("selected_run_id")
    if not run_id:
        st.warning("Select a run on the home page first.")
        st.page_link("app.py", label="Choose a run", icon="⬅️")
        st.stop()
    return settings, load_run(settings, run_id)

