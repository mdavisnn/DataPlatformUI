import streamlit as st

from components.console import render_hero
from services.page_views import run_page_view


render_hero(
    "PROJECT REVIEW",
    "Projects & findings",
    "A project-comparison viewpoint pairing cross-domain health measures with "
    "their deterministic findings. Use it to locate concentrated conditions "
    "and trace them back to governed evidence.",
    icon=":material/grid_view:",
)

view = st.segmented_control(
    "Projects and findings view",
    ["Project health", "All findings"],
    default="Project health",
    key="projects_findings_view",
    persist_state="session",
)

run_page_view("findings" if view == "All findings" else "project_health")
