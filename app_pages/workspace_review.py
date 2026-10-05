import streamlit as st

from components.console import render_hero
from services.page_views import run_page_view


render_hero(
    "WORKSPACE",
    "Workspace",
    "An observation-wide executive viewpoint over portfolio scale, diagnostic "
    "coverage, evidence limitations and priority signals. Use it to orient the "
    "review and confirm that the evidence is fit before interpreting results.",
    icon=":material/home:",
)

view = st.segmented_control(
    "Workspace view",
    ["Overview", "Evidence & fitness"],
    default="Overview",
    key="workspace_review_view",
    persist_state="session",
)

run_page_view("evidence" if view == "Evidence & fitness" else "workspace")
