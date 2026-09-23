"""Read-only schedule lens over one diagnosed canonical observation."""

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from components.console import render_hero, render_metric_row
from services.console_context import console_context
from services.lenses import diagnostic_outcome, product_reference
from services.platform_reader import MetadataReadError


def _percent(value) -> str:
    return "Unavailable" if value is None else f"{value}%"


def _read_product(catalogue, outcome, name):
    reference = product_reference(outcome, name)
    if not reference:
        raise ValueError(f"Schedule product {name!r} is not recorded")
    return catalogue.read_table(reference)


_, catalogue, client_id, snapshot = console_context()

render_hero(
    "Point-in-time diagnostic",
    "Schedule lens",
    "Inspect overdue work, milestone position, activity duration and schedule "
    "structure using products calculated by DataPlatform for this observation.",
    icon=":material/calendar_month:",
)

if not snapshot:
    st.info("No diagnosed observation is available.")
    st.stop()

snapshot_id = snapshot["snapshot_id"]
bundle = catalogue.snapshot_bundle(snapshot_id, client_id)
outcome = diagnostic_outcome(bundle["diagnosis"], "schedule")
if not outcome or outcome.get("status") != "success":
    st.info(
        "The schedule lens is unavailable for this observation. Run a current "
        "schedule diagnosis or review its capability fitness."
    )
    st.stop()

try:
    project_summary = _read_product(
        catalogue, outcome, "project_summary"
    )
    activity_profile = _read_product(
        catalogue, outcome, "activity_profile"
    )
    conditions = _read_product(catalogue, outcome, "conditions")
except (FileNotFoundError, ValueError, MetadataReadError) as error:
    st.warning(f"Schedule lens evidence is unavailable: {error}")
    st.stop()

metrics = outcome.get("metrics", {})
render_metric_row([
    ("Activities", metrics.get("tasks_analysed")),
    ("Milestones", metrics.get("milestone_count")),
    ("Overdue activities", metrics.get("overdue_tasks")),
    ("Overdue milestones", metrics.get("overdue_milestones")),
    ("Projects with conditions", metrics.get("projects_with_conditions")),
])

filter_columns = st.columns(2)
project_ids = sorted(
    project_summary.get("ProjectID", pd.Series(dtype=str))
    .dropna().astype(str).unique().tolist()
)
project_names = {
    str(row.ProjectID): (
        f"{row.ProjectName} | {row.ProjectID}"
        if str(row.ProjectName).strip() else str(row.ProjectID)
    )
    for row in project_summary[
        ["ProjectID", "ProjectName"]
    ].itertuples(index=False)
}
selected_project = filter_columns[0].selectbox(
    "Project",
    [None, *project_ids],
    format_func=lambda value: (
        "All projects" if value is None else project_names.get(value, value)
    ),
    key=f"schedule_project_{snapshot_id}",
)
health_options = [
    value for value in ("Poor", "Warning", "Healthy")
    if value in set(project_summary.get("ScheduleHealth", []))
]
selected_health = filter_columns[1].pills(
    "Schedule health",
    health_options,
    selection_mode="multi",
    key=f"schedule_health_{snapshot_id}",
)

filtered_summary = project_summary.copy()
filtered_activity = activity_profile.copy()
filtered_conditions = conditions.copy()
if selected_project is not None:
    filtered_summary = filtered_summary[
        filtered_summary["ProjectID"].astype(str) == selected_project
    ]
    filtered_activity = filtered_activity[
        filtered_activity["ProjectID"].astype(str) == selected_project
    ]
    filtered_conditions = filtered_conditions[
        filtered_conditions["ProjectID"].astype(str) == selected_project
    ]
if selected_health:
    visible_ids = set(
        filtered_summary.loc[
            filtered_summary["ScheduleHealth"].isin(selected_health),
            "ProjectID",
        ].astype(str)
    )
    filtered_summary = filtered_summary[
        filtered_summary["ProjectID"].astype(str).isin(visible_ids)
    ]
    filtered_activity = filtered_activity[
        filtered_activity["ProjectID"].astype(str).isin(visible_ids)
    ]
    filtered_conditions = filtered_conditions[
        filtered_conditions["ProjectID"].astype(str).isin(visible_ids)
    ]

st.subheader("Where schedule conditions are concentrated")
condition_columns = [
    column for column in (
        "OverdueTasks", "OverdueMilestones", "VeryLongTasks",
        "TasksStartingBeforeProject", "TasksFinishingAfterProject",
    )
    if column in filtered_summary
]
if filtered_summary.empty:
    st.info("No projects match the selected filters.")
elif condition_columns:
    chart_rows = filtered_summary.copy()
    chart_rows["Project"] = chart_rows.apply(
        lambda row: (
            str(row.get("ProjectName") or row.get("ProjectID"))
        ),
        axis=1,
    )
    st.bar_chart(
        chart_rows,
        x="Project",
        y=condition_columns,
        stack=True,
        width="stretch",
    )

distribution_column, milestone_column = st.columns(2)
with distribution_column:
    st.subheader("Activity duration distribution")
    durations = filtered_activity.copy()
    durations["DurationDays"] = pd.to_numeric(
        durations.get("DurationDays"), errors="coerce"
    )
    durations = durations.dropna(subset=["DurationDays"])
    if durations.empty:
        st.info("No usable activity durations are available in this scope.")
    else:
        chart = (
            alt.Chart(durations)
            .mark_bar(color="#46637f")
            .encode(
                x=alt.X(
                    "DurationDays:Q",
                    bin=alt.Bin(maxbins=12),
                    title="Duration (days)",
                ),
                y=alt.Y("count():Q", title="Activities"),
                tooltip=[
                    alt.Tooltip(
                        "DurationDays:Q",
                        bin=alt.Bin(maxbins=12),
                        title="Duration band",
                    ),
                    alt.Tooltip("count():Q", title="Activities"),
                ],
            )
        )
        st.altair_chart(chart, width="stretch")

with milestone_column:
    st.subheader("Milestone position")
    milestones = filtered_activity[
        filtered_activity.get(
            "IsMilestone", pd.Series(False, index=filtered_activity.index)
        ).fillna(False).astype(bool)
    ]
    milestone_fields = [
        column for column in (
            "ProjectName", "TaskName", "ForecastFinish", "Status",
            "IsOverdue", "FinishVarianceDays", "TotalFloatDays",
        )
        if column in milestones
    ]
    if milestones.empty:
        st.info("No milestone evidence is available in this scope.")
    else:
        st.dataframe(
            milestones[milestone_fields],
            hide_index=True,
            width="stretch",
        )

st.subheader("Schedule structure and evidence coverage")
coverage_fields = [
    column for column in (
        "ProjectName", "ScheduleHealth", "TaskCount", "MilestoneCount",
        "DateCoveragePct", "HierarchyCoveragePct", "FloatCoveragePct",
        "CriticalEvidenceCoveragePct", "BaselineFinishCoveragePct",
        "MedianTaskDurationDays", "MaxTaskDurationDays",
    )
    if column in filtered_summary
]
st.dataframe(
    filtered_summary[coverage_fields],
    hide_index=True,
    width="stretch",
)

st.subheader("Deterministic schedule conditions")
condition_fields = [
    column for column in (
        "Severity", "RuleID", "ProjectName", "TaskName", "TaskStart",
        "TaskFinish", "Status", "Message",
    )
    if column in filtered_conditions
]
if filtered_conditions.empty:
    st.info("No schedule conditions were produced in this scope.")
else:
    st.dataframe(
        filtered_conditions[condition_fields],
        hide_index=True,
        width="stretch",
    )

with st.expander("Evidence limits"):
    st.write(
        "Date coverage: "
        f"{_percent(metrics.get('date_coverage_pct'))}; "
        "hierarchy coverage: "
        f"{_percent(metrics.get('hierarchy_coverage_pct'))}; "
        "float coverage: "
        f"{_percent(metrics.get('float_coverage_pct'))}."
    )
    unavailable = metrics.get("unavailable_measures", [])
    if unavailable:
        st.caption(
            "Unavailable measures: "
            + ", ".join(
                str(item).replace("_", " ") for item in unavailable
            )
            + "."
        )
    st.caption(
        "The health label and condition flags are backend diagnostic outputs. "
        "Chart bins and filters are presentation-only."
    )
