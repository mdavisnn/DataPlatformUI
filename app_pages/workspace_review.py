import streamlit as st

from components.console import render_hero
from services.page_views import run_page_view


current_view = st.session_state.get("workspace_review_view", "Overview")
hero = {
    "Overview": (
        "Overview",
        "From evidence to better decisions",
        "Balance portfolio position, evidence reliability and priority "
        "diagnostic signals in one executive view.",
        ":material/home:",
    ),
    "Evidence & fitness": (
        "Evidence",
        "Can this evidence support the analysis?",
        "Review structural fitness, limitations and unavailable diagnostic "
        "rules before interpreting delivery conditions.",
        ":material/fact_check:",
    ),
}[current_view]
render_hero(*hero[:3], icon=hero[3])

view = st.segmented_control(
    "Workspace view",
    ["Overview", "Evidence & fitness"],
    default="Overview",
    key="workspace_review_view",
    persist_state="session",
)

run_page_view("evidence" if view == "Evidence & fitness" else "workspace")
