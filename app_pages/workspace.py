"""Executive snapshot for one governed canonical observation."""

import pandas as pd
import streamlit as st

from components.console import render_finding, render_hero, render_metric_row
from services.console_context import console_context


_, catalogue, client_id, snapshot = console_context()

render_hero(
    "Point-in-time diagnostic",
    "Executive snapshot",
    "Understand the scale of the observation, where deterministic "
    "exceptions are concentrated and which evidence limitations matter.",
    icon=":material/analytics:",
)

if not snapshot:
    st.info(
        "No assessed observations are available yet. Open Run the lab or "
        "seed the synthetic demo.",
        icon=":material/info:",
    )
    st.stop()

bundle = catalogue.snapshot_bundle(snapshot["snapshot_id"], client_id)
diagnosis = bundle["diagnosis"]
summary = diagnosis.get("summary") or {}
findings = bundle["findings"].get("findings", [])

st.caption(
    f"Client {client_id} | observation "
    f"{snapshot.get('observation_date', 'undated')} | "
    f"snapshot {snapshot.get('snapshot_id', 'unknown')}"
)

if not summary:
    st.warning(
        "This observation predates the executive-summary contract. Its "
        "saved fitness and Findings remain available on the other pages.",
        icon=":material/history:",
    )
    st.stop()

scale = summary.get("portfolio_scale", {})
finding_summary = summary.get("findings", {})
render_metric_row([
    ("Projects", scale.get("projects")),
    ("Activities", scale.get("tasks")),
    ("Milestones", scale.get("milestones")),
    ("Resources", scale.get("resources")),
    ("Findings", finding_summary.get("total")),
    ("Projects affected", finding_summary.get("projects_affected")),
])

st.subheader("Assessment coverage")
diagnostic_summary = summary.get("diagnostics", {})
fitness_summary = summary.get("fitness", {})
render_metric_row([
    ("Diagnostics completed", diagnostic_summary.get("completed")),
    ("Diagnostics skipped", diagnostic_summary.get("skipped")),
    ("Diagnostics failed", diagnostic_summary.get("failed")),
    ("Fitness blockers", fitness_summary.get("blocking_conditions")),
    ("Fitness caveats", fitness_summary.get("caveats")),
    ("Unavailable rules", fitness_summary.get("unavailable_rules")),
])

if (
    fitness_summary.get("blocking_conditions", 0)
    or fitness_summary.get("caveats", 0)
    or fitness_summary.get("unavailable_rules", 0)
):
    st.warning(
        "Evidence limitations apply to this observation. Review Evidence & "
        "fitness before interpreting the diagnostic signals.",
        icon=":material/warning:",
    )

st.subheader("Exception concentration")
domain_counts = finding_summary.get("by_domain", {})
if domain_counts:
    concentration = pd.DataFrame([
        {
            "Domain": str(domain).replace("_", " ").title(),
            "Findings": int(count),
        }
        for domain, count in domain_counts.items()
    ]).sort_values("Findings", ascending=False)
    st.bar_chart(
        concentration,
        x="Domain",
        y="Findings",
        horizontal=True,
        height=300,
    )
else:
    st.info(
        "No deterministic findings were produced. This does not by itself "
        "establish that the portfolio is healthy."
    )

st.subheader("Priority findings")
ordered = sorted(
    findings,
    key=lambda item: (
        {"high": 0, "medium": 1, "low": 2}.get(
            item.get("severity"), 9
        ),
        str(item.get("domain", "")),
        str(item.get("rule_id", "")),
    ),
)
if not ordered:
    st.caption("No Findings are available for this observation.")
for finding in ordered[:5]:
    render_finding(finding)
