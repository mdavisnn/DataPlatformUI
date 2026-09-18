import streamlit as st


def render_status_badge(status: str) -> None:
    normalised = status.lower()
    icon = "✅" if normalised in {"success", "completed", "pass", "passed"} else "⚠️" if normalised not in {"unknown", "not_started"} else "➖"
    st.markdown(f"### {icon} {status.replace('_', ' ').title()}")

