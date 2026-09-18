"""Deterministic Finding exploration."""

import streamlit as st

from components.console import render_finding, render_hero, render_metric_row
from services.catalog import findings_frame
from services.console_context import console_context
from services.platform_reader import MetadataReadError


_, catalogue, client_id, snapshot = console_context()

render_hero(
    "Diagnose",
    "What is happening?",
    "Findings are deterministic signals. Open any finding to inspect the evidence, affected entities and rule that produced it.",
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
        "No deterministic findings were produced. This does not by itself establish that the portfolio is healthy."
    )
    st.stop()

render_metric_row([
    ("Total findings", len(findings)),
    ("High", sum(item.get("severity") == "high" for item in findings)),
    ("Medium", sum(item.get("severity") == "medium" for item in findings)),
    ("Domains", frame["Domain"].nunique()),
])

filter_columns = st.columns(2)
domains = filter_columns[0].multiselect("Domain", sorted(frame["Domain"].unique()))
severities = filter_columns[1].pills(
    "Severity", ["High", "Medium", "Low"], selection_mode="multi"
)
selected = findings
if domains:
    selected = [
        item for item in selected if item.get("domain", "").title() in domains
    ]
if severities:
    selected = [
        item
        for item in selected
        if item.get("severity", "").title() in severities
    ]

chart = findings_frame({"findings": selected})
if not chart.empty:
    counts = (
        chart.groupby(["Domain", "Severity"])
        .size()
        .reset_index(name="Findings")
    )
    st.bar_chart(
        counts,
        x="Domain",
        y="Findings",
        color="Severity",
        stack=True,
        height=300,
    )

for finding in selected:
    render_finding(finding)
    details = st.expander(
        f"Evidence · {finding.get('finding_id', 'Unknown')}",
        icon=":material/database:",
        on_change="rerun",
    )
    if details.open:
        with details:
            evidence = finding.get("evidence", {})
            if evidence:
                st.table(evidence, border="horizontal", width="content")
            entities = finding.get("affected_entities", {})
            for entity_type, values in entities.items():
                st.caption(f"{entity_type.replace('_', ' ').title()} ({len(values)})")
                st.write(", ".join(map(str, values)))
            for reference in finding.get("supporting_artifacts", []):
                st.markdown(f"**{reference}**")
                try:
                    st.dataframe(catalogue.read_table(reference), hide_index=True)
                except (FileNotFoundError, ValueError, MetadataReadError) as error:
                    st.warning(f"Supporting evidence is unavailable: {error}")
