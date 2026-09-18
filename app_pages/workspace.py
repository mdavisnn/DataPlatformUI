"""Consultant workspace overview."""

import streamlit as st

from components.console import render_finding, render_hero, render_metric_row
from services.console_context import console_context


_, catalogue, client_id, snapshot = console_context()

render_hero(
    "Delivery intelligence · Data Lab",
    "From evidence to better decisions",
    "Understand what was supplied, test what it can support and explore traceable diagnostic findings.",
    icon=":material/analytics:",
)

workflow_columns = st.columns(3, border=True)
for column, step, title, description in zip(
    workflow_columns,
    ("01", "02", "03"),
    ("Understand", "Assess", "Diagnose"),
    (
        "Discover and profile the evidence.",
        "Establish fitness by capability.",
        "Review findings and supporting proof.",
    ),
):
    with column:
        st.caption(step)
        st.subheader(title)
        st.write(description)

if not snapshot:
    st.info(
        "No assessed observations are available yet. Open Run the lab or seed the synthetic demo.",
        icon=":material/info:",
    )
    st.stop()

bundle = catalogue.snapshot_bundle(snapshot["snapshot_id"], client_id)
findings = bundle["findings"].get("findings", [])
fitness = bundle["fitness"].get("capabilities", {})
render_metric_row([
    ("Observation", snapshot.get("observation_date", "—")),
    ("Datasets", len(snapshot.get("datasets", {}))),
    ("Findings", len(findings)),
    ("Capabilities fit", sum(value.get("status") == "fit" for value in fitness.values())),
])

st.subheader("Priority signals")
ordered = sorted(
    findings,
    key=lambda item: {"high": 0, "medium": 1, "low": 2}.get(item.get("severity"), 9),
)
if not ordered:
    st.info(
        "No deterministic findings were produced. This does not by itself establish that the portfolio is healthy."
    )
for finding in ordered[:3]:
    render_finding(finding)
