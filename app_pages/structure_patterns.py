import streamlit as st

from components.console import render_hero
from services.page_views import run_page_view


render_hero(
    "STRUCTURAL REVIEW",
    "Structure & patterns",
    "A structural and peer-pattern viewpoint across dependencies and saved "
    "distributions. Use it to identify coupling, concentrations and unusual "
    "values for investigation, without inferring causes.",
    icon=":material/account_tree:",
)

view = st.segmented_control(
    "Structure and patterns view",
    ["Dependencies", "Patterns"],
    default="Dependencies",
    key="structure_patterns_view",
    persist_state="session",
)

run_page_view("patterns" if view == "Patterns" else "dependencies")
