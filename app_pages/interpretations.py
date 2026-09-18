"""Recorded human interpretation sessions."""

import streamlit as st

from components.console import render_hero, status_badge
from services.console_context import console_context, safe


_, catalogue, _ = console_context()

render_hero(
    "Interpret",
    "What might the findings mean?",
    "Interpretations remain visibly separate from deterministic evidence and retain their cited Finding IDs.",
    icon=":material/psychology:",
)

sessions = safe(catalogue.list_interpretations, [])
if not sessions:
    st.info("No recorded interpretations are available yet.")
    st.stop()

for session in sessions:
    with st.container(border=True):
        st.subheader(session.get("interpretation_id", "Interpretation"))
        st.markdown(status_badge(session.get("review_status")))
        st.table(
            {
                "Source type": session.get("source_type", "—"),
                "Source ID": session.get("source_id", "—"),
                "Latest revision": session.get("latest_revision", "—"),
            },
            border="horizontal",
            width="content",
        )
