import streamlit as st

from components.console import render_hero
from services.page_views import run_page_view


render_hero(
    "SCHEDULE REVIEW",
    "Schedule & plan",
    "A time-and-sequencing viewpoint from schedule conditions through to dated "
    "project and task plans. Use it to understand delivery exposure and where "
    "supported findings sit in the plan.",
    icon=":material/view_timeline:",
)

view = st.segmented_control(
    "Schedule and plan view",
    ["Schedule conditions", "Plan on a page"],
    default="Schedule conditions",
    key="schedule_plan_view",
    persist_state="session",
)

run_page_view("plan" if view == "Plan on a page" else "schedule")
