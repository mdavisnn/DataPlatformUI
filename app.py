"""Streamlit entry point for the DataPlatform consultant console."""

from __future__ import annotations

import streamlit as st

from components.console import render_observation_context
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

review_pages = [
    st.Page(
        "app_pages/workspace_review.py",
        title="Workspace",
        icon=":material/home:",
    ),
    st.Page(
        "app_pages/projects_findings.py",
        title="Projects & findings",
        icon=":material/grid_view:",
    ),
    st.Page(
        "app_pages/schedule_plan.py",
        title="Schedule & plan",
        icon=":material/view_timeline:",
    ),
    st.Page(
        "app_pages/resources.py",
        title="Resources",
        icon=":material/groups:",
    ),
    st.Page(
        "app_pages/structure_patterns.py",
        title="Structure & patterns",
        icon=":material/account_tree:",
    ),
    st.Page(
        "app_pages/history.py",
        title="History",
        icon=":material/timeline:",
    ),
]
act_pages = [
    st.Page(
        "app_pages/scenario_planning.py",
        title="Scenario planning",
        icon=":material/event_repeat:",
    ),
    st.Page(
        "app_pages/run_lab.py",
        title="Run the lab",
        icon=":material/play_circle:",
    ),
]
page = st.navigation(
    {"Review": review_pages, "Act": act_pages},
    position="hidden",
)

with st.sidebar:
    st.header("Data Lab", icon=":material/analytics:")
    st.markdown("**Review**")
    for review_page in review_pages:
        st.page_link(review_page, width="stretch")
    st.markdown("**Act**")
    for act_page in act_pages:
        st.page_link(act_page, width="stretch")

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
    st.divider()
    st.subheader("Data scope", icon=":material/database:")
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

selected_snapshot = next(
    (
        item
        for item in snapshots
        if item.get("snapshot_id")
        == st.session_state.get("selected_snapshot_id")
    ),
    None,
)
render_observation_context(
    client_id=st.session_state.get("selected_client_id"),
    observation_date=(selected_snapshot or {}).get("observation_date"),
    snapshot_id=st.session_state.get("selected_snapshot_id"),
)

page.run()
