"""Deterministic Finding exploration."""

from __future__ import annotations

import hashlib

import pandas as pd
import streamlit as st

from components.console import MetricCard, render_hero, render_metric_row, render_panel
from components.finding_review import render_finding_detail
from services.catalog import findings_frame
from services.console_context import console_context
from services.findings import (
    filter_findings,
    finding_review_frame,
    sort_findings,
)


_, catalogue, client_id, snapshot = console_context()

render_hero(
    "Diagnose",
    "What is happening?",
    "Review deterministic Findings, then trace the selected condition to its "
    "recorded rule, affected entities and governed supporting evidence.",
    icon=":material/search_insights:",
)

if not snapshot:
    st.info("No diagnosed observation is available.")
    st.stop()

bundle = catalogue.snapshot_bundle(snapshot["snapshot_id"], client_id)
findings = bundle["findings"].get("findings", [])
frame = findings_frame(bundle["findings"])
if frame.empty:
    st.info(
        "No deterministic findings were produced. This does not by itself "
        "establish that the portfolio is healthy."
    )
    st.stop()

render_metric_row([
    MetricCard(
        "Total findings",
        len(findings),
        icon=":material/description:",
    ),
    MetricCard(
        "High severity",
        sum(item.get("severity") == "high" for item in findings),
        icon=":material/error:",
    ),
    MetricCard(
        "Medium severity",
        sum(item.get("severity") == "medium" for item in findings),
        icon=":material/warning:",
    ),
    MetricCard(
        "Domains",
        frame["Domain"].nunique(),
        icon=":material/grid_view:",
    ),
])

snapshot_id = snapshot["snapshot_id"]
domain_key = f"finding_domains_{snapshot_id}"
severity_key = f"finding_severities_{snapshot_id}"
sort_key = f"finding_sort_{snapshot_id}"


def _clear_finding_filters() -> None:
    st.session_state[domain_key] = []
    st.session_state[severity_key] = []
    st.session_state[sort_key] = "Severity"


with st.container(border=True):
    st.markdown("**Filter the diagnostic view**")
    filter_columns = st.columns([1.4, 1.2, 1.0, 0.7], vertical_alignment="bottom")
    domains = filter_columns[0].multiselect(
        "Domain",
        sorted(frame["Domain"].unique()),
        key=domain_key,
        persist_state="page",
    )
    severities = filter_columns[1].pills(
        "Severity",
        ["High", "Medium", "Low"],
        selection_mode="multi",
        key=severity_key,
        persist_state="page",
    )
    sort_by = filter_columns[2].selectbox(
        "Sort by",
        ["Severity", "Domain", "Title"],
        key=sort_key,
        persist_state="page",
    )
    filter_columns[3].button(
        "Clear",
        icon=":material/filter_alt_off:",
        on_click=_clear_finding_filters,
        width="stretch",
    )

selected = sort_findings(
    filter_findings(
        findings,
        domains=domains,
        severities=severities,
    ),
    sort_by,
)

if not selected:
    st.info(
        "No Findings match the current filters.",
        icon=":material/search_off:",
    )
    st.stop()

selected_frame = findings_frame({"findings": selected})
summary_columns = st.columns(2)
with summary_columns[0]:
    with render_panel(
        "Findings by severity",
        "Counts for the current filtered view.",
        icon=":material/priority_high:",
    ):
        severity_counts = (
            selected_frame["Severity"]
            .value_counts()
            .reindex(["High", "Medium", "Low"], fill_value=0)
            .rename_axis("Severity")
            .reset_index(name="Findings")
        )
        st.bar_chart(
            severity_counts,
            x="Severity",
            y="Findings",
            height=240,
        )
with summary_columns[1]:
    with render_panel(
        "Findings by domain",
        "Counts for the current filtered view.",
        icon=":material/category:",
    ):
        domain_counts = (
            selected_frame.groupby("Domain")
            .size()
            .reset_index(name="Findings")
            .sort_values("Findings", ascending=False)
        )
        st.bar_chart(
            domain_counts,
            x="Domain",
            y="Findings",
            height=240,
        )

st.subheader("Findings and evidence")
st.caption(
    "Select one Finding to inspect its deterministic rule context and the "
    "governed evidence that supports it."
)

list_column, detail_column = st.columns([1.05, 1.25], gap="medium")
with list_column:
    with st.container(border=True):
        st.markdown(f"**Findings ({len(selected)})**")
        review_frame = finding_review_frame(selected)
        selection_signature = hashlib.sha256(
            "|".join(
                str(item.get("finding_id", "")) for item in selected
            ).encode("utf-8")
        ).hexdigest()[:10]
        event = st.dataframe(
            review_frame,
            hide_index=True,
            width="stretch",
            height=500,
            key=f"finding_index_{snapshot_id}_{selection_signature}",
            on_select="rerun",
            selection_mode="single-row-required",
            selection_default={"selection": {"rows": [0]}},
            column_order=["Severity", "Title", "Domain", "Affected"],
            column_config={
                "Severity": st.column_config.TextColumn(width="small"),
                "Title": st.column_config.TextColumn(width="large", pinned=True),
                "Domain": st.column_config.TextColumn(width="small"),
                "Affected": st.column_config.NumberColumn(width="small"),
            },
        )
        selected_rows = list(event.selection.rows)
        selected_index = selected_rows[0] if selected_rows else 0

with detail_column:
    with st.container(border=True):
        render_finding_detail(
            catalogue,
            selected[selected_index],
            bundle.get("fitness", {}),
        )
