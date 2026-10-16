import streamlit as st

from components.console import render_hero
from services.page_views import run_page_view


current_view = st.session_state.get(
    "structure_patterns_view", "Dependencies"
)
hero = {
    "Dependencies": (
        "Dependencies",
        "Where is delivery coupled?",
        "Review governed dependency structure, cross-project links and "
        "concentrations without inferring causes.",
        ":material/account_tree:",
    ),
    "Patterns": (
        "Patterns",
        "What looks unusual?",
        "Explore saved distributions and unusual values as investigative "
        "signals rather than proof of poor performance.",
        ":material/query_stats:",
    ),
}[current_view]
render_hero(*hero[:3], icon=hero[3])

view = st.segmented_control(
    "Structure and patterns view",
    ["Dependencies", "Patterns"],
    default="Dependencies",
    key="structure_patterns_view",
    persist_state="session",
)

run_page_view("patterns" if view == "Patterns" else "dependencies")
