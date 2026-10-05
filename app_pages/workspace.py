"""Executive snapshot for one governed canonical observation."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from components.console import (
    MetricCard,
    render_finding,
    render_hero,
    render_metric_row,
    render_panel,
)
from components.project_profile import attention_map_chart
from services.console_context import console_context
from services.project_profile import (
    prepare_attention_map,
    selected_attention_project,
)


_, catalogue, client_id, snapshot = console_context()

render_hero(
    "Point-in-time diagnostic",
    "Executive snapshot",
    "Understand the scale of the observation, whether its evidence supports "
    "analysis, and where deterministic conditions require attention.",
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
    MetricCard(
        "Projects",
        scale.get("projects"),
        icon=":material/folder:",
    ),
    MetricCard(
        "Activities",
        scale.get("tasks"),
        icon=":material/checklist:",
    ),
    MetricCard(
        "Findings",
        finding_summary.get("total"),
        icon=":material/description:",
    ),
    MetricCard(
        "Projects affected",
        finding_summary.get("projects_affected"),
        icon=":material/flag:",
    ),
])

diagnostic_summary = summary.get("diagnostics", {})
fitness_summary = summary.get("fitness", {})
capabilities = bundle.get("fitness", {}).get("capabilities", {})
fit_capabilities = sum(
    assessment.get("status") == "fit"
    for assessment in capabilities.values()
)

overview_columns = st.columns(3)
with overview_columns[0]:
    with render_panel(
        "Evidence scale",
        "Canonical evidence in this observation.",
        icon=":material/database:",
    ):
        render_metric_row([
            ("Milestones", scale.get("milestones")),
            ("Resources", scale.get("resources")),
        ])
        st.caption(
            f"{len(bundle.get('snapshot', {}).get('datasets', {}))} canonical "
            "dataset(s) referenced by the snapshot."
        )
with overview_columns[1]:
    with render_panel(
        "Diagnostic coverage",
        "Backend diagnostic execution recorded for this snapshot.",
        icon=":material/analytics:",
    ):
        render_metric_row([
            ("Completed", diagnostic_summary.get("completed")),
            ("Skipped", diagnostic_summary.get("skipped")),
            ("Failed", diagnostic_summary.get("failed")),
        ])
with overview_columns[2]:
    with render_panel(
        "Evidence fitness",
        "Fitness limitations remain separate from delivery conditions.",
        icon=":material/fact_check:",
    ):
        render_metric_row([
            ("Capabilities fit", fit_capabilities),
            ("Blockers", fitness_summary.get("blocking_conditions")),
            ("Caveats", fitness_summary.get("caveats")),
        ])
        unavailable_rules = fitness_summary.get("unavailable_rules", 0)
        st.caption(f"{unavailable_rules} diagnostic rule(s) unavailable.")

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

finding_charts = st.columns(2)
with finding_charts[0]:
    with render_panel(
        "Findings by domain",
        "Where deterministic conditions are concentrated.",
        icon=":material/category:",
    ):
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
                height=270,
            )
        else:
            st.caption("No deterministic Findings were produced.")
with finding_charts[1]:
    with render_panel(
        "Findings by severity",
        "Severity assigned by the recorded diagnostic rules.",
        icon=":material/priority_high:",
    ):
        severity_counts = bundle.get("findings", {}).get(
            "counts_by_severity", {}
        )
        if severity_counts:
            severity_frame = pd.DataFrame([
                {
                    "Severity": severity.title(),
                    "Findings": int(severity_counts.get(severity, 0)),
                }
                for severity in ("high", "medium", "low")
            ])
            st.bar_chart(
                severity_frame,
                x="Severity",
                y="Findings",
                height=270,
            )
        else:
            st.caption("No severity counts were recorded.")

st.subheader("Portfolio attention map")
st.caption(
    "Each project is positioned by the share of tasks with schedule "
    "conditions and the share of assigned resources with conflicts. Bubble "
    "size reflects saved dependency connectivity; colour reflects Finding "
    "severity. The dashed lines are the governed portfolio medians."
)
profile = catalogue.read_table(diagnosis["project_profile_object"])
project_health = catalogue.read_table(diagnosis["project_health_object"])
attention = prepare_attention_map(profile, project_health)
plottable = attention[attention["Plottable"]]
if plottable.empty:
    st.info(
        "No projects have both schedule-condition and resource-conflict "
        "measures for this observation."
    )
else:
    attention_event = st.altair_chart(
        attention_map_chart(attention),
        key=f"attention_map_{snapshot['snapshot_id']}",
        on_select="rerun",
        selection_mode="project_select",
        width="stretch",
    )
    attention_project_id = selected_attention_project(attention_event)
    if attention_project_id:
        selected_row = attention[
            attention["ProjectID"].astype(str) == attention_project_id
        ].iloc[0]
        selected_findings = [
            finding
            for finding in findings
            if attention_project_id
            in {
                str(value)
                for value in finding.get("affected_entities", {}).get(
                    "projects", []
                )
            }
        ]
        with st.container(border=True):
            st.subheader(selected_row["ProjectLabel"])
            render_metric_row([
                (
                    "Schedule-condition tasks",
                    f"{selected_row['ScheduleConditionPct']:.1f}%",
                ),
                (
                    "Conflict resources",
                    f"{selected_row['ConflictResourcePct']:.1f}%",
                ),
                ("Findings", int(selected_row["FindingCount"])),
            ])
            if selected_findings:
                for finding in selected_findings[:3]:
                    render_finding(finding)
            else:
                st.caption("No deterministic Findings affect this project.")

unplottable = attention[~attention["Plottable"]]
if not unplottable.empty:
    st.caption(
        f"{len(unplottable)} project(s) are not plotted because a required "
        "schedule or resource ratio is unavailable."
    )
    st.dataframe(
        unplottable[["ProjectName", "ProjectID", "DataFitness"]],
        hide_index=True,
        width="stretch",
    )

st.subheader("Priority findings")
st.caption(
    "Highest-severity deterministic conditions in this observation. Open the "
    "Findings view to inspect their rule and supporting evidence."
)
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
for finding in ordered[:3]:
    render_finding(finding)


def _show_evidence_fitness() -> None:
    st.session_state["workspace_review_view"] = "Evidence & fitness"


with st.container(horizontal=True, wrap=True):
    if st.button(
        "Review all findings",
        icon=":material/arrow_forward:",
        type="primary",
    ):
        st.session_state["projects_findings_view"] = "All findings"
        st.switch_page("app_pages/projects_findings.py")
    st.button(
        "Review evidence fitness",
        icon=":material/fact_check:",
        on_click=_show_evidence_fitness,
    )
    if st.button(
        "Review history",
        icon=":material/timeline:",
    ):
        st.switch_page("app_pages/history.py")
