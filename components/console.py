"""Reusable presentation components for the Data Lab console."""

from __future__ import annotations

from typing import Any

import streamlit as st


def render_hero(eyebrow: str, title: str, description: str, *, icon: str) -> None:
    st.caption(eyebrow.upper())
    st.title(title, icon=icon)
    st.write(description)


def render_metric_row(metrics: list[tuple[str, Any]]) -> None:
    with st.container(horizontal=True):
        for label, value in metrics:
            st.metric(label, "—" if value is None else value, border=True)


def status_badge(status: str | None) -> str:
    normalised = str(status or "unknown").lower()
    color = {
        "fit": "green",
        "fit_with_caveats": "orange",
        "not_fit": "red",
        "high": "red",
        "medium": "orange",
        "low": "green",
    }.get(normalised, "gray")
    label = normalised.replace("_", " ").title()
    return f":{color}-badge[{label}]"


def render_finding(finding: dict[str, Any]) -> None:
    evidence = finding.get("evidence", {})
    evidence_text = " · ".join(
        f"{key.replace('_', ' ').title()}: {value}"
        for key, value in evidence.items()
        if not isinstance(value, (dict, list))
    )
    with st.container(border=True):
        st.markdown(status_badge(finding.get("severity")))
        st.subheader(finding.get("title", "Untitled finding"))
        st.write(finding.get("description", ""))
        metadata = " · ".join(
            value
            for value in (
                str(finding.get("domain", "")).upper(),
                str(finding.get("rule_id", "No rule")),
                evidence_text,
            )
            if value
        )
        st.caption(metadata)
