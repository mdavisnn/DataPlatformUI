"""Portfolio-to-project, single-snapshot diagnostic timeline."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from components.console import render_finding, render_hero, render_metric_row
from components.timeline import (
    diagnostic_timeline_chart,
    portfolio_timeline_chart,
)
from services.console_context import console_context
from services.platform_reader import MetadataReadError
from services.timeline import (
    build_finding_occurrences,
    build_project_finding_occurrences,
    findings_for_project,
    findings_for_projects,
    portfolio_groups,
    prepare_portfolio_schedule,
    prepare_project_schedule,
    project_ids_for_portfolio,
    selected_finding_id,
    selected_project_id,
)


def _passes_filters(
    finding: dict,
    domains: list[str],
    severities: list[str],
) -> bool:
    return (
        not domains
        or str(finding.get("domain", "unknown")).title() in domains
    ) and (
        not severities
        or str(finding.get("severity", "unknown")).title() in severities
    )


def _finding_rows(findings: list[dict]) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "Finding": finding.get("title", "Untitled finding"),
            "Domain": str(finding.get("domain", "unknown")).title(),
            "Severity": str(finding.get("severity", "unknown")).title(),
            "Rule": finding.get("rule_id", ""),
        }
        for finding in findings
    ])


_, catalogue, client_id, snapshot = console_context()

render_hero(
    "Diagnose in context",
    "Plan on a page",
    "Compare project forecast windows and deterministic findings by portfolio, "
    "then select a project to inspect its task timeline. The selected "
    "observation remains the sole analytical scope.",
    icon=":material/view_timeline:",
)

if not snapshot:
    st.info("No diagnosed observation is available.")
    st.stop()

snapshot_id = snapshot["snapshot_id"]
bundle = catalogue.snapshot_bundle(snapshot_id, client_id)
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

portfolio_options = [None, *portfolio_groups(projects)]
selected_portfolio = st.selectbox(
    "Portfolio",
    portfolio_options,
    format_func=lambda value: "All portfolios" if value is None else value,
    key=f"plan_portfolio_{snapshot_id}",
)

try:
    scoped_project_ids = project_ids_for_portfolio(
        projects,
        selected_portfolio,
    )
    project_schedule, excluded_projects = prepare_portfolio_schedule(
        projects,
        selected_portfolio,
    )
except ValueError as error:
    st.warning(str(error))
    st.stop()

if not scoped_project_ids:
    st.info("No projects are available in this portfolio scope.")
    st.stop()

portfolio_findings = findings_for_projects(
    findings,
    scoped_project_ids,
    tasks,
)
domains = sorted({
    str(item.get("domain", "unknown")).title()
    for item in portfolio_findings
})
severities = [
    severity
    for severity in ("High", "Medium", "Low", "Unknown")
    if any(
        str(item.get("severity", "unknown")).title() == severity
        for item in portfolio_findings
    )
]

filter_columns = st.columns(2)
selected_domains = filter_columns[0].multiselect(
    "Finding domain",
    domains,
    key=f"plan_domains_{snapshot_id}",
)
selected_severities = filter_columns[1].pills(
    "Finding severity",
    severities,
    selection_mode="multi",
    key=f"plan_severity_{snapshot_id}",
)
visible_portfolio_findings = [
    finding
    for finding in portfolio_findings
    if _passes_filters(
        finding,
        selected_domains,
        selected_severities,
    )
]

artifact_frames: dict[str, pd.DataFrame] = {}
unavailable_artifacts: list[str] = []
references = sorted({
    str(reference)
    for finding in visible_portfolio_findings
    for reference in finding.get("supporting_artifacts", [])
})
for reference in references:
    try:
        artifact_frames[reference] = catalogue.read_table(reference)
    except (FileNotFoundError, ValueError, MetadataReadError):
        unavailable_artifacts.append(reference)

project_occurrences = build_project_finding_occurrences(
    project_schedule,
    tasks,
    visible_portfolio_findings,
    artifact_frames,
)
dated_portfolio_finding_ids = set(
    project_occurrences["FindingID"].astype(str)
)
undated_portfolio_findings = [
    finding
    for finding in visible_portfolio_findings
    if str(finding.get("finding_id", ""))
    not in dated_portfolio_finding_ids
]

render_metric_row([
    ("Projects plotted", len(project_schedule)),
    (
        "Portfolios",
        int(project_schedule["PortfolioGroup"].nunique())
        if not project_schedule.empty
        else 0,
    ),
    ("Relevant findings", len(visible_portfolio_findings)),
    ("Dated overlays", len(project_occurrences)),
])

portfolio_token = str(selected_portfolio or "all")
chart_event = None
with st.container(border=True):
    st.subheader(
        "All portfolios"
        if selected_portfolio is None
        else str(selected_portfolio)
    )
    st.caption(
        f"Observation {manifest.get('observation_date', 'undated')} · "
        "neutral bars are project forecast windows; coloured marks are dated "
        "finding evidence."
    )
    if project_schedule.empty:
        st.info("No projects in this scope have usable forecast dates.")
    else:
        chart_event = st.altair_chart(
            portfolio_timeline_chart(
                project_schedule,
                project_occurrences,
                manifest.get("observation_date"),
            ),
            width="stretch",
            key=f"portfolio_chart_{snapshot_id}_{portfolio_token}",
            on_select="rerun",
            selection_mode="project_pick",
        )
        st.caption(
            "Select a project bar or coloured overlay to drill into its task "
            "timeline. Double-click the chart to clear the chart selection."
        )

if excluded_projects:
    st.warning(
        f"{excluded_projects} project row(s) were not plotted because their "
        "forecast dates or identity were missing or invalid."
    )
if unavailable_artifacts:
    st.warning(
        f"{len(unavailable_artifacts)} supporting artifact(s) could not be "
        "read; affected findings remain listed without a dated overlay."
    )

scope_rows = projects.loc[
    projects["ProjectID"].astype("string").isin(scoped_project_ids),
    ["ProjectID", "ProjectName"],
].dropna(subset=["ProjectID"])
scope_rows = scope_rows.drop_duplicates(subset=["ProjectID"])
scope_rows["ProjectID"] = scope_rows["ProjectID"].astype(str)
scope_rows["ProjectName"] = scope_rows["ProjectName"].fillna(
    scope_rows["ProjectID"]
).astype(str)
scope_rows = scope_rows.sort_values(["ProjectName", "ProjectID"])
project_labels = {
    str(row.ProjectID): f"{row.ProjectName} · {row.ProjectID}"
    for row in scope_rows.itertuples(index=False)
}

project_key = f"plan_project_{snapshot_id}_{portfolio_token}"
last_chart_project_key = f"{project_key}_last_chart"
chart_project_id = selected_project_id(chart_event)
last_chart_project = st.session_state.get(last_chart_project_key)
if chart_project_id != last_chart_project:
    if chart_project_id in project_labels:
        st.session_state[project_key] = chart_project_id
    st.session_state[last_chart_project_key] = chart_project_id
if (
    st.session_state.get(project_key) is not None
    and st.session_state.get(project_key) not in project_labels
):
    del st.session_state[project_key]

project_id = st.selectbox(
    "Drill into project",
    list(project_labels),
    index=None,
    placeholder="Select a project bar or choose a project",
    format_func=project_labels.get,
    key=project_key,
)

if undated_portfolio_findings:
    with st.expander(
        "Portfolio findings without dated evidence "
        f"({len(undated_portfolio_findings)})"
    ):
        st.caption(
            "These findings affect projects in the current scope, but their "
            "supporting evidence does not establish a defensible timeline "
            "period."
        )
        st.dataframe(
            _finding_rows(undated_portfolio_findings),
            hide_index=True,
        )

if not project_id:
    st.info("Select a project to open its task timeline.")
    st.stop()

project_task_rows = tasks.loc[
    tasks["ProjectID"].astype("string") == str(project_id)
] if "ProjectID" in tasks else pd.DataFrame()
project_task_ids = (
    project_task_rows["TaskID"].dropna().astype(str).tolist()
    if "TaskID" in project_task_rows
    else []
)
project_findings = findings_for_project(
    visible_portfolio_findings,
    project_id,
    project_task_ids,
)

try:
    schedule, excluded_tasks = prepare_project_schedule(tasks, project_id)
except ValueError as error:
    st.warning(str(error))
    st.stop()

occurrences = build_finding_occurrences(
    schedule,
    project_findings,
    artifact_frames,
)
dated_finding_ids = set(occurrences["FindingID"].astype(str))
undated_findings = [
    finding
    for finding in project_findings
    if str(finding.get("finding_id", "")) not in dated_finding_ids
]

st.divider()
st.header(project_labels[project_id])
render_metric_row([
    ("Tasks plotted", len(schedule)),
    (
        "Milestones",
        int(schedule["IsMilestone"].sum()) if not schedule.empty else 0,
    ),
    ("Project findings", len(project_findings)),
    ("Dated overlays", len(occurrences)),
])

task_chart_event = None
with st.container(border=True):
    st.subheader("Task timeline")
    st.caption(
        "Neutral bars are forecast tasks; coloured marks are dated finding "
        "evidence from the selected snapshot."
    )
    if schedule.empty:
        st.info("This project has no tasks with usable forecast dates.")
    else:
        task_chart = diagnostic_timeline_chart(
            schedule,
            occurrences,
            manifest.get("observation_date"),
        )
        if occurrences.empty:
            st.altair_chart(task_chart, width="stretch")
        else:
            task_chart_event = st.altair_chart(
                task_chart,
                width="stretch",
                key=f"plan_chart_{snapshot_id}_{project_id}",
                on_select="rerun",
                selection_mode="finding_pick",
            )
            st.caption(
                "Select a coloured overlay to inspect its finding. "
                "Double-click the chart to clear the selection."
            )

if excluded_tasks:
    st.warning(
        f"{excluded_tasks} task row(s) were not plotted because their "
        "forecast dates were missing or invalid."
    )

finding_by_id = {
    str(finding.get("finding_id", "")): finding
    for finding in project_findings
}
finding_key = f"plan_finding_{snapshot_id}_{project_id}"
last_chart_finding_key = f"{finding_key}_last_chart"
chart_finding_id = selected_finding_id(task_chart_event)
last_chart_finding = st.session_state.get(last_chart_finding_key)
if chart_finding_id != last_chart_finding:
    if chart_finding_id in finding_by_id:
        st.session_state[finding_key] = chart_finding_id
    st.session_state[last_chart_finding_key] = chart_finding_id
if (
    st.session_state.get(finding_key) is not None
    and st.session_state.get(finding_key) not in finding_by_id
):
    del st.session_state[finding_key]

if finding_by_id:
    selected_id = st.selectbox(
        "Inspect finding",
        list(finding_by_id),
        index=None,
        placeholder="Select a finding",
        format_func=lambda finding_id: (
            f"{finding_by_id[finding_id].get('title', 'Untitled finding')} · "
            f"{str(finding_by_id[finding_id].get('severity', 'unknown')).title()}"
        ),
        key=finding_key,
    )
else:
    selected_id = None

if selected_id and selected_id in finding_by_id:
    st.subheader("Finding detail")
    render_finding(finding_by_id[selected_id])
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
    st.subheader("Project findings without dated evidence")
    st.caption(
        "These findings affect the selected project or its tasks, but their "
        "supporting evidence does not establish a defensible timeline period."
    )
    st.dataframe(_finding_rows(undated_findings), hide_index=True)
