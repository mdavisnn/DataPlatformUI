import streamlit as st

from components.console import render_hero
from services.page_views import run_page_view


current_view = st.session_state.get(
    "projects_findings_view", "Project health"
)
hero = {
    "Project health": (
        "Projects",
        "Where is attention concentrated?",
        "Compare cross-domain project conditions and locate concentrations "
        "that warrant closer review.",
        ":material/grid_view:",
    ),
    "All findings": (
        "Findings",
        "What is happening?",
        "Select a deterministic condition and trace it to its rule, affected "
        "entities and governed evidence.",
        ":material/search_insights:",
    ),
}[current_view]
render_hero(*hero[:3], icon=hero[3])

view = st.segmented_control(
    "Projects and findings view",
    ["Project health", "All findings"],
    default="Project health",
    key="projects_findings_view",
    persist_state="session",
)

run_page_view("findings" if view == "All findings" else "project_health")
