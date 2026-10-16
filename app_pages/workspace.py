"""Executive snapshot for one governed canonical observation."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from components.console import (
    MetricCard,
    render_finding,
    render_finding_signal,
    render_hero,
    render_metric_row,
    render_panel,
)
from components.diagnostic_charts import (
    domain_distribution_chart,
    severity_distribution_chart,
)
from components.project_profile import attention_map_chart
from services.console_context import console_context
from services.project_profile import (
    prepare_attention_map,
    selected_attention_project,
)


_, catalogue, client_id, snapshot = console_context()

render_hero(
    "Overview",
    "From evidence to better decisions",
    "Balance portfolio position, evidence reliability and priority diagnostic "
    "signals in one executive view.",
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
diagnostic_summary = summary.get("diagnostics", {})
fitness_summary = summary.get("fitness", {})
capabilities = bundle.get("fitness", {}).get("capabilities", {})
fit_capabilities = sum(
    assessment.get("status") == "fit"
    for assessment in capabilities.values()
)
capability_count = len(capabilities)

render_metric_row([
    MetricCard(
        "Projects",
        scale.get("projects"),
        icon=":material/folder:",
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
    MetricCard(
        "Evidence fitness",
        f"{fit_capabilities}/{capability_count} fit"
        if capability_count else "Not assessed",
        icon=":material/fact_check:",
    ),
])

with render_panel(
    "Observation coverage",
    "A compact view of evidence scale, diagnostic execution and fitness.",
    icon=":material/data_check:",
):
    with st.container(
        horizontal=True,
        wrap=True,
        horizontal_alignment="distribute",
        gap="medium",
    ):
        st.markdown(
            "**Evidence scale**  \n"
            f"{scale.get('tasks', 0)} activities · "
            f"{scale.get('milestones', 0)} milestones · "
            f"{scale.get('resources', 0)} resources · "
            f"{len(bundle.get('snapshot', {}).get('datasets', {}))} datasets"
        )
        st.markdown(
            "**Diagnostic coverage**  \n"
            f"{diagnostic_summary.get('completed', 0)} completed · "
            f"{diagnostic_summary.get('skipped', 0)} skipped · "
            f"{diagnostic_summary.get('failed', 0)} failed"
        )
        st.markdown(
            "**Evidence limitations**  \n"
            f"{fitness_summary.get('blocking_conditions', 0)} blockers · "
            f"{fitness_summary.get('caveats', 0)} caveats · "
            f"{fitness_summary.get('unavailable_rules', 0)} unavailable rules"
        )

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

profile = catalogue.read_table(diagnosis["project_profile_object"])
project_health = catalogue.read_table(diagnosis["project_health_object"])
attention = prepare_attention_map(profile, project_health)
plottable = attention[attention["Plottable"]]

map_column, signals_column = st.columns([1.75, 1], gap="medium")
with map_column:
    with render_panel(
        "Portfolio attention map",
        "Projects are positioned by saved schedule-condition and resource-"
        "conflict ratios. Size reflects dependency connectivity; colour "
        "reflects Finding severity.",
        icon=":material/bubble_chart:",
    ):
        if plottable.empty:
            st.info(
                "No projects have both schedule-condition and resource-"
                "conflict measures for this observation."
            )
        else:
            attention_event = st.altair_chart(
                attention_map_chart(attention),
                key=f"attention_map_{snapshot['snapshot_id']}",
                on_select="rerun",
                selection_mode="project_select",
                width="stretch",
            )
            st.caption(
                "Dashed lines show governed portfolio medians. Select a "
                "project for its recorded conditions and Findings."
            )
            attention_project_id = selected_attention_project(
                attention_event
            )
            if attention_project_id:
                selected_row = attention[
                    attention["ProjectID"].astype(str)
                    == attention_project_id
                ].iloc[0]
                selected_findings = [
                    finding
                    for finding in findings
                    if attention_project_id
                    in {
                        str(value)
                        for value in finding.get(
                            "affected_entities", {}
                        ).get("projects", [])
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
                        st.caption(
                            "No deterministic Findings affect this project."
                        )

with signals_column:
    with render_panel(
        "Priority signals",
        "Highest-severity deterministic conditions in this observation.",
        icon=":material/priority_high:",
    ):
        if not ordered:
            st.caption("No Findings are available for this observation.")
        for finding in ordered[:3]:
            render_finding_signal(finding)

unplottable = attention[~attention["Plottable"]]
if not unplottable.empty:
    unavailable = st.expander(
        f"Projects outside the attention map ({len(unplottable)})",
        icon=":material/hide_source:",
        on_change="rerun",
    )
    if unavailable.open:
        with unavailable:
            st.caption(
                "A required schedule or resource ratio is unavailable."
            )
            st.dataframe(
                unplottable[["ProjectName", "ProjectID", "DataFitness"]],
                hide_index=True,
                width="stretch",
            )

distribution = st.expander(
    "Finding distribution",
    icon=":material/bar_chart:",
    on_change="rerun",
)
if distribution.open:
    with distribution:
        distribution_columns = st.columns(2)
        with distribution_columns[0]:
            st.markdown("**By domain**")
            domain_counts = finding_summary.get("by_domain", {})
            if domain_counts:
                concentration = pd.DataFrame([
                    {
                        "Domain": str(domain).replace("_", " ").title(),
                        "Findings": int(count),
                    }
                    for domain, count in domain_counts.items()
                ])
                st.altair_chart(
                    domain_distribution_chart(concentration),
                    width="stretch",
                )
            else:
                st.caption("No deterministic Findings were produced.")
        with distribution_columns[1]:
            st.markdown("**By severity**")
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
                st.altair_chart(
                    severity_distribution_chart(severity_frame),
                    width="stretch",
                )
            else:
                st.caption("No severity counts were recorded.")


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
