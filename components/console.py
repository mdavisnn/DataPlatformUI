"""Reusable presentation components for the Data Lab console."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

import streamlit as st

from services.findings import affected_entity_count


_SUPPRESS_PAGE_HERO: ContextVar[bool] = ContextVar(
    "_SUPPRESS_PAGE_HERO",
    default=False,
)


@dataclass(frozen=True)
class MetricCard:
    """Presentation options for a native Streamlit metric card."""

    label: str
    value: Any
    delta: Any | None = None
    delta_color: str = "normal"
    help: str | None = None
    icon: str | None = None
    delta_description: str | None = None


@contextmanager
def suppress_page_hero() -> Iterator[None]:
    """Suppress a nested page hero only for the current render context."""
    token = _SUPPRESS_PAGE_HERO.set(True)
    try:
        yield
    finally:
        _SUPPRESS_PAGE_HERO.reset(token)


def render_hero(eyebrow: str, title: str, description: str, *, icon: str) -> None:
    """Render the standard page context, title, and purpose statement."""

    if _SUPPRESS_PAGE_HERO.get():
        return
    st.caption(eyebrow.upper())
    st.title(title, icon=icon)
    st.write(description)


def _metric_card(metric: MetricCard | tuple[str, Any]) -> MetricCard:
    if isinstance(metric, MetricCard):
        return metric
    label, value = metric
    return MetricCard(label=label, value=value)


def render_metric_row(
    metrics: list[MetricCard | tuple[str, Any]],
) -> None:
    """Render a responsive row of consistently bordered metric cards."""

    with st.container(horizontal=True, gap="small"):
        for item in metrics:
            metric = _metric_card(item)
            st.metric(
                metric.label,
                metric.value,
                metric.delta,
                delta_color=metric.delta_color,
                help=metric.help,
                icon=metric.icon,
                delta_description=metric.delta_description,
                border=True,
                height="stretch",
            )


@contextmanager
def render_panel(
    title: str | None = None,
    description: str | None = None,
    *,
    icon: str | None = None,
) -> Iterator[None]:
    """Render a standard analytical panel without business logic."""

    with st.container(border=True, gap="small"):
        if title:
            st.subheader(title, icon=icon)
        if description:
            st.caption(description)
        yield


def render_observation_context(
    *,
    client_id: str | None,
    observation_date: str | None,
    snapshot_id: str | None,
) -> None:
    """Keep business observation identity visible in the shared app shell."""

    with st.container(
        border=True,
        horizontal=True,
        wrap=True,
        horizontal_alignment="distribute",
        vertical_alignment="center",
        gap="small",
    ):
        st.markdown(
            f"**Client**  \n{client_id or 'No client selected'}"
        )
        st.markdown(
            f"**Observation**  \n{observation_date or 'Not available'}"
        )
        st.markdown(
            f"**Snapshot**  \n{snapshot_id or 'Not available'}"
        )
        if client_id == "demo-ui":
            st.badge(
                "Synthetic demo",
                icon=":material/science:",
                color="orange",
            )


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
    evidence_text = " \N{MIDDLE DOT} ".join(
        f"{key.replace('_', ' ').title()}: {value}"
        for key, value in evidence.items()
        if not isinstance(value, (dict, list))
    )
    with st.container(border=True):
        st.markdown(status_badge(finding.get("severity")))
        st.subheader(finding.get("title", "Untitled finding"))
        st.caption(finding.get("finding_id", "Unknown Finding ID"))
        st.write(finding.get("description", ""))
        metadata = " \N{MIDDLE DOT} ".join(
            value
            for value in (
                str(finding.get("domain", "")).upper(),
                str(finding.get("rule_id", "No rule")),
                f"{affected_entity_count(finding)} affected reference(s)",
                evidence_text,
            )
            if value
        )
        st.caption(metadata)
