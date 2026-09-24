"""Streamlit entry point for the DataPlatform consultant console."""

from __future__ import annotations

import streamlit as st

from components.exit_control import render_exit_control
from config.settings import Settings, SettingsError
from services.catalog import Catalogue
from services.console_context import safe


st.set_page_config(
    page_title="Data Lab | Delivery intelligence",
    page_icon=":material/analytics:",
    layout="wide",
    initial_sidebar_state="expanded",
)

with st.sidebar:
    st.header("Data Lab", icon=":material/analytics:")
    st.caption("PPM diagnostic workspace")

try:
    settings = Settings.from_environment()
    catalogue = Catalogue(settings)
    clients = safe(catalogue.list_clients, [])
except SettingsError as error:
    with st.sidebar:
        st.divider()
        render_exit_control()
    st.error(str(error), icon=":material/error:")
    st.info(
        "Set DATALAB_PLATFORM_PATH in .env to the DataPlatform repository root.",
        icon=":material/settings:",
    )
    st.stop()

st.session_state.setdefault("selected_client_id", None)
st.session_state.setdefault("selected_snapshot_id", None)

with st.sidebar:
    snapshots = []
    if clients:
        current_client = st.session_state.get("selected_client_id")
        if current_client not in clients:
            current_client = clients[0]
        selected_client = st.selectbox(
            "Client",
            clients,
            index=clients.index(current_client),
            key="client_selector",
        )
        if selected_client != st.session_state.get("selected_client_id"):
            st.session_state["selected_snapshot_id"] = None
            st.session_state.pop(
                f"observation_selector_{selected_client}",
                None,
            )
        st.session_state["selected_client_id"] = selected_client
        snapshots = safe(
            lambda: catalogue.list_snapshots(selected_client),
            [],
        )
    else:
        st.session_state["selected_client_id"] = None
        st.session_state["selected_snapshot_id"] = None
        st.caption("No client-scoped evidence is available yet.")

    if snapshots:
        labels = {
            (
                f"{item.get('observation_date', 'Undated')} | "
                f"{item['snapshot_id']}"
            ): item["snapshot_id"]
            for item in snapshots
        }
        current_snapshot = st.session_state.get("selected_snapshot_id")
        default_index = next(
            (
                index
                for index, value in enumerate(labels.values())
                if value == current_snapshot
            ),
            0,
        )
        selection = st.selectbox(
            "Observation",
            list(labels),
            index=default_index,
            key=f"observation_selector_{st.session_state['selected_client_id']}",
        )
        st.session_state["selected_snapshot_id"] = labels[selection]
    elif clients:
        st.session_state["selected_snapshot_id"] = None
        st.caption("No assessed observations are available for this client.")
    st.caption(f"Storage: {settings.storage_root}")
    st.divider()
    render_exit_control()

page = st.navigation(
    {
        "Review": [
            st.Page(
                "app_pages/workspace.py",
                title="Workspace",
                icon=":material/home:",
            ),
            st.Page(
                "app_pages/evidence.py",
                title="Evidence & fitness",
                icon=":material/fact_check:",
            ),
            st.Page(
                "app_pages/findings.py",
                title="Findings",
                icon=":material/search_insights:",
            ),
            st.Page(
                "app_pages/project_health.py",
                title="Project health",
                icon=":material/grid_view:",
            ),
            st.Page(
                "app_pages/schedule.py",
                title="Schedule",
                icon=":material/calendar_month:",
            ),
            st.Page(
                "app_pages/resources.py",
                title="Resources",
                icon=":material/groups:",
            ),
            st.Page(
                "app_pages/dependencies.py",
                title="Dependencies",
                icon=":material/account_tree:",
            ),
            st.Page(
                "app_pages/patterns.py",
                title="Patterns",
                icon=":material/scatter_plot:",
            ),
            st.Page(
                "app_pages/plan.py",
                title="Plan on a page",
                icon=":material/view_timeline:",
            ),
            st.Page(
                "app_pages/history.py",
                title="History",
                icon=":material/timeline:",
            ),
            st.Page(
                "app_pages/interpretations.py",
                title="Interpretations",
                icon=":material/psychology:",
            ),
        ],
        "Operate": [
            st.Page(
                "app_pages/run_lab.py",
                title="Run the lab",
                icon=":material/play_circle:",
            ),
        ],
    }
)
page.run()
