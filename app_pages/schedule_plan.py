import streamlit as st

from components.console import render_hero
from services.page_views import run_page_view


current_view = st.session_state.get(
    "schedule_plan_view", "Schedule assessment"
)
hero = {
    "Schedule assessment": (
        "Schedule",
        "Where is the plan exposed?",
        "Review deterministic schedule conditions, coverage and supporting "
        "activity evidence.",
        ":material/assessment:",
    ),
    "Plan on a page": (
        "Plan",
        "When is the work expected to happen?",
        "Place projects, activities and dated findings into a governed "
        "forecast timeline.",
        ":material/view_timeline:",
    ),
}[current_view]
render_hero(*hero[:3], icon=hero[3])

view = st.segmented_control(
    "Schedule and plan view",
    ["Schedule assessment", "Plan on a page"],
    default="Schedule assessment",
    key="schedule_plan_view",
    persist_state="session",
)

run_page_view("plan" if view == "Plan on a page" else "schedule")
