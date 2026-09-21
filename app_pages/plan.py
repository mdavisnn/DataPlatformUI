"""Single-project, single-snapshot diagnostic timeline prototype."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from components.console import render_finding, render_hero, render_metric_row
from components.timeline import diagnostic_timeline_chart
from services.console_context import console_context
from services.platform_reader import MetadataReadError
from services.timeline import (
    build_finding_occurrences,
    findings_for_project,
    prepare_project_schedule,
    selected_finding_id,
)


_, catalogue, client_id, snapshot = console_context()

render_hero(
    "Diagnose in context",
    "Plan on a page",
    "Review one project's forecast plan and the dated evidence behind its deterministic findings. The selected observation remains the sole analytical scope.",
    icon=":material/view_timeline:",
)

if not snapshot:
    st.info("No diagnosed observation is available.")
    st.stop()

bundle = catalogue.snapshot_bundle(snapshot["snapshot_id"], client_id)
manifest = bundle["snapshot"]
findings = bundle["findings"].get("findings", [])

try:
    projects = catalogue.read_snapshot_dataset(manifest, "projects")
    tasks = catalogue.read_snapshot_dataset(manifest, "tasks")
except (FileNotFoundError, ValueError, MetadataReadError) as error:
    st.warning(
        "This observation cannot yet support the plan-on-a-page view: "
        f"{error}"
    )
    st.stop()

required_project_fields = {"ProjectID", "ProjectName"}
if not required_project_fields.issubset(projects.columns):
    st.warning("The canonical projects dataset has no usable project identity.")
    st.stop()

project_rows = (
    projects[["ProjectID", "ProjectName"]]
    .dropna(subset=["ProjectID"])
    .drop_duplicates(subset=["ProjectID"])
    .sort_values(["ProjectName", "ProjectID"])
)
if project_rows.empty:
    st.info("No projects are available in this observation.")
    st.stop()

project_labels = {
    str(row.ProjectID): f"{row.ProjectName} · {row.ProjectID}"
    for row in project_rows.itertuples(index=False)
}
project_id = st.selectbox(
    "Project",
    list(project_labels),
    format_func=project_labels.get,
    key=f"plan_project_{snapshot['snapshot_id']}",
)

try:
    schedule, excluded_tasks = prepare_project_schedule(tasks, project_id)
except ValueError as error:
    st.warning(str(error))
    st.stop()

if schedule.empty:
    st.info("This project has no tasks with usable forecast dates.")
    if excluded_tasks:
        st.caption(
            f"{excluded_tasks} task row(s) were not plotted because their "
            "forecast dates were missing or invalid."
        )
    st.stop()

project_findings = findings_for_project(
    findings,
    project_id,
    schedule["TaskID"],
)
domains = sorted({
    str(item.get("domain", "unknown")).title()
    for item in project_findings
})
severities = [
    severity
    for severity in ("High", "Medium", "Low")
    if any(
        str(item.get("severity", "unknown")).title() == severity
        for item in project_findings
    )
]

filter_columns = st.columns(2)
selected_domains = filter_columns[0].multiselect(
    "Finding domain",
    domains,
    key=f"plan_domains_{snapshot['snapshot_id']}_{project_id}",
)
selected_severities = filter_columns[1].pills(
    "Finding severity",
    severities,
    selection_mode="multi",
    key=f"plan_severity_{snapshot['snapshot_id']}_{project_id}",
)
visible_findings = [
    finding
    for finding in project_findings
    if (
        not selected_domains
        or str(finding.get("domain", "unknown")).title()
        in selected_domains
    )
    and (
        not selected_severities
        or str(finding.get("severity", "unknown")).title()
        in selected_severities
    )
]

artifact_frames: dict[str, pd.DataFrame] = {}
unavailable_artifacts: list[str] = []
references = sorted({
    str(reference)
    for finding in visible_findings
    for reference in finding.get("supporting_artifacts", [])
})
for reference in references:
    try:
        artifact_frames[reference] = catalogue.read_table(reference)
    except (FileNotFoundError, ValueError, MetadataReadError):
        unavailable_artifacts.append(reference)

occurrences = build_finding_occurrences(
    schedule,
    visible_findings,
    artifact_frames,
)
dated_finding_ids = set(occurrences["FindingID"].astype(str))
undated_findings = [
    finding
    for finding in visible_findings
    if str(finding.get("finding_id", "")) not in dated_finding_ids
]

render_metric_row([
    ("Tasks", len(schedule)),
    ("Milestones", int(schedule["IsMilestone"].sum())),
    ("Relevant findings", len(visible_findings)),
    ("Dated overlays", len(occurrences)),
])

with st.container(border=True):
    st.subheader(project_labels[project_id])
    st.caption(
        f"Observation {manifest.get('observation_date', 'undated')} · "
        "Neutral bars are forecast tasks; coloured marks are dated finding evidence."
    )
    chart = diagnostic_timeline_chart(
        schedule,
        occurrences,
        manifest.get("observation_date"),
    )
    if occurrences.empty:
        st.altair_chart(chart, width="stretch")
        chart_event = None
    else:
        chart_event = st.altair_chart(
            chart,
            width="stretch",
            key=f"plan_chart_{snapshot['snapshot_id']}_{project_id}",
            on_select="rerun",
            selection_mode="finding_pick",
        )
        st.caption(
            "Select a coloured overlay to inspect its Finding. Double-click the chart to clear the selection."
        )

if excluded_tasks:
    st.warning(
        f"{excluded_tasks} task row(s) were not plotted because their forecast "
        "dates were missing or invalid."
    )
if unavailable_artifacts:
    st.warning(
        f"{len(unavailable_artifacts)} supporting artifact(s) could not be read; "
        "affected findings remain listed without a dated overlay."
    )

selected_from_chart = selected_finding_id(chart_event)
finding_by_id = {
    str(finding.get("finding_id", "")): finding
    for finding in visible_findings
}
if finding_by_id:
    manual_finding_id = st.selectbox(
        "Inspect finding",
        list(finding_by_id),
        index=None,
        placeholder="Select a finding",
        format_func=lambda finding_id: (
            f"{finding_by_id[finding_id].get('title', 'Untitled finding')} · "
            f"{str(finding_by_id[finding_id].get('severity', 'unknown')).title()}"
        ),
        key=f"plan_finding_{snapshot['snapshot_id']}_{project_id}",
    )
else:
    manual_finding_id = None
selected_id = selected_from_chart or manual_finding_id

if selected_id and selected_id in finding_by_id:
    st.subheader("Finding detail")
    selected_finding = finding_by_id[selected_id]
    render_finding(selected_finding)
    selected_occurrences = occurrences.loc[
        occurrences["FindingID"] == selected_id,
        ["TaskID", "Start", "Finish", "TimeBasis", "Detail"],
    ]
    if not selected_occurrences.empty:
        st.dataframe(
            selected_occurrences,
            hide_index=True,
            column_config={
                "Start": st.column_config.DatetimeColumn(
                    "Evidence start", format="DD MMM YYYY"
                ),
                "Finish": st.column_config.DatetimeColumn(
                    "Evidence finish", format="DD MMM YYYY"
                ),
            },
        )

if undated_findings:
    st.subheader("Findings without dated evidence")
    st.caption(
        "These Findings affect the selected project or its tasks, but their "
        "supporting evidence does not establish a defensible timeline period."
    )
    st.dataframe(
        pd.DataFrame([
            {
                "Finding": finding.get("title", "Untitled finding"),
                "Domain": str(finding.get("domain", "unknown")).title(),
                "Severity": str(
                    finding.get("severity", "unknown")
                ).title(),
                "Rule": finding.get("rule_id", ""),
            }
            for finding in undated_findings
        ]),
        hide_index=True,
    )
