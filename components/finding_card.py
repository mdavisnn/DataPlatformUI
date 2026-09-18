import streamlit as st


def render_finding(title: str, evidence: str, severity: str = "info", next_step: str | None = None) -> None:
    renderer = st.error if severity.lower() == "high" else st.warning if severity.lower() == "medium" else st.info
    renderer(f"**{title}**\n\n{evidence}")
    if next_step:
        st.caption(f"Suggested investigation: {next_step}")

