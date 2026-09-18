"""Streamlit entry point for the DataPlatform consultant console."""

from __future__ import annotations

import streamlit as st

from config.settings import Settings, SettingsError
from services.catalog import Catalogue
from services.console_context import safe


st.set_page_config(
    page_title="Data Lab | Delivery intelligence",
    page_icon=":material/analytics:",
    layout="wide",
    initial_sidebar_state="expanded",
)

try:
    settings = Settings.from_environment()
    catalogue = Catalogue(settings)
    snapshots = safe(catalogue.list_snapshots, [])
except SettingsError as error:
    st.error(str(error), icon=":material/error:")
    st.info(
        "Set DATALAB_PLATFORM_PATH in .env to the DataPlatform repository root.",
        icon=":material/settings:",
    )
    st.stop()

with st.sidebar:
    st.header("Data Lab", icon=":material/analytics:")
    st.caption("PPM diagnostic workspace")
    if snapshots:
        labels = {
            f"{item.get('observation_date', 'Undated')} · {item['snapshot_id']}": item["snapshot_id"]
            for item in snapshots
        }
        current = st.session_state.get("selected_snapshot_id")
        default_index = next(
            (index for index, value in enumerate(labels.values()) if value == current),
            0,
        )
        selection = st.selectbox("Observation", list(labels), index=default_index)
        st.session_state["selected_snapshot_id"] = labels[selection]
    else:
        st.session_state["selected_snapshot_id"] = None
        st.caption("No assessed observations are available yet.")
    st.caption(f"Storage: {settings.storage_root}")

page = st.navigation(
    {
        "Review": [
            st.Page("app_pages/workspace.py", title="Workspace", icon=":material/home:"),
            st.Page("app_pages/evidence.py", title="Evidence & fitness", icon=":material/fact_check:"),
            st.Page("app_pages/findings.py", title="Findings", icon=":material/search_insights:"),
            st.Page("app_pages/history.py", title="History", icon=":material/timeline:"),
            st.Page("app_pages/interpretations.py", title="Interpretations", icon=":material/psychology:"),
        ],
        "Operate": [
            st.Page("app_pages/run_lab.py", title="Run the lab", icon=":material/play_circle:"),
        ],
    }
)
page.run()
