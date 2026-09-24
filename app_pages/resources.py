"""Read-only resource lens over one diagnosed canonical observation."""

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from components.console import render_hero, render_metric_row
from components.resource_charts import allocation_pressure_chart
from services.console_context import console_context
from services.lenses import diagnostic_outcome, product_reference
from services.platform_reader import MetadataReadError


def _percent(value) -> str:
    return "Unavailable" if value is None else f"{value}%"


def _read_product(catalogue, outcome, name):
    reference = product_reference(outcome, name)
    if not reference:
        raise ValueError(f"Resource product {name!r} is not recorded")
    return catalogue.read_table(reference)


def _contains_identifier(values: pd.Series, identifier: str) -> pd.Series:
    return values.fillna("").astype(str).map(
        lambda value: identifier in {
            item.strip() for item in value.split(",") if item.strip()
        }
    )


def _true_values(values: pd.Series) -> pd.Series:
    return values.fillna(False).map(
        lambda value: value is True
        or str(value).strip().lower() == "true"
    )


def _allocation_pressure(resource_summary, metrics):
    st.subheader("Allocation pressure across people")
    st.caption(
        "Compares each person's highest concurrent planned allocation with "
        "the configured conflict threshold."
    )
    pressure = resource_summary.copy()
    pressure["PeakConcurrentAllocationPct"] = pd.to_numeric(
        pressure.get("PeakConcurrentAllocationPct"), errors="coerce"
    )
    pressure = pressure.dropna(
        subset=["PeakConcurrentAllocationPct"]
    ).head(25)
    if pressure.empty:
        st.info("No dated allocation pressure evidence is available.")
        return
    chart = allocation_pressure_chart(
        pressure,
        metrics.get("conflict_threshold_pct", 100),
    )
    st.altair_chart(chart, width="stretch")


def _summary_view(resource_summary, conflicts, metrics):
    st.subheader("Resource lens summary")
    st.caption(
        "A portfolio-wide view of planned allocation pressure, shared people "
        "and the conflict periods produced by the configured rule."
    )
    _allocation_pressure(resource_summary, metrics)

    st.subheader("Resource concentration and cross-project usage")
    st.caption(
        "Shows how assignments are concentrated and which people are planned "
        "across more than one project."
    )
    resource_fields = [
        column for column in (
            "ResourceName", "ResourceID", "Role", "Team", "CapacityPct",
            "AssignmentCount", "TaskCount", "ProjectCount", "CrossProject",
            "AssignmentAllocationSharePct", "PeakConcurrentAllocationPct",
            "ConflictPeriodCount", "AssignmentDateCoveragePct",
        )
        if column in resource_summary
    ]
    if resource_summary.empty:
        st.info("No resource evidence is available.")
    else:
        st.dataframe(
            resource_summary[resource_fields],
            hide_index=True,
            width="stretch",
        )

    st.subheader("Conflict periods")
    st.caption(
        "Each row is a period when overlapping planned assignments exceeded "
        "the configured allocation threshold."
    )
    conflict_fields = [
        column for column in (
            "ResourceName", "ResourceID", "ConflictStart", "ConflictFinish",
            "TotalAllocation", "OverAllocation", "ProjectCount", "TaskCount",
            "ProjectIDs", "TaskIDs",
        )
        if column in conflicts
    ]
    if conflicts.empty:
        st.info("No over-allocation conflict periods were identified.")
    else:
        st.dataframe(
            conflicts[conflict_fields],
            hide_index=True,
            width="stretch",
        )


def _person_view(
    resource_summary,
    assignment_timeline,
    conflicts,
    snapshot_id,
    metrics,
):
    st.subheader("Plan on a page by person")
    st.caption(
        "Select a person to see planned work across projects. Bar colours "
        "show the conflict status calculated by DataPlatform."
    )
    if assignment_timeline.empty:
        st.info(
            "Assignment timeline evidence is not available for this "
            "observation. Run a current resource diagnosis to create it."
        )
        return

    resource_ids = sorted(
        assignment_timeline["ResourceID"].dropna().astype(str).unique()
    )
    names = {
        str(row.ResourceID): (
            f"{row.ResourceName} | {row.ResourceID}"
            if str(row.ResourceName).strip() else str(row.ResourceID)
        )
        for row in resource_summary[
            ["ResourceID", "ResourceName"]
        ].itertuples(index=False)
    }
    conflict_ids = set(
        conflicts.get("ResourceID", pd.Series(dtype=str))
        .dropna().astype(str)
    )
    default_id = next(
        (resource_id for resource_id in resource_ids
         if resource_id in conflict_ids),
        resource_ids[0],
    )
    selected = st.selectbox(
        "Person",
        resource_ids,
        index=resource_ids.index(default_id),
        format_func=lambda value: names.get(value, value),
        key=f"resource_person_{snapshot_id}",
    )
    person = assignment_timeline[
        assignment_timeline["ResourceID"].astype(str) == selected
    ].copy()
    if "ConflictStatus" not in person:
        person["ConflictStatus"] = _true_values(
            person.get(
                "OverlapsConflict",
                pd.Series(False, index=person.index),
            )
        ).map({True: "Amber", False: "Green"})
    if "PeakConflictAllocationPct" not in person:
        person["PeakConflictAllocationPct"] = pd.NA
    person_conflicts = conflicts[
        conflicts.get("ResourceID", pd.Series(dtype=str)).astype(str)
        == selected
    ].copy()
    complete = _true_values(
        person.get("DateComplete", pd.Series(False, index=person.index))
    )
    dated = person[complete].copy()
    dated["DisplayStart"] = pd.to_datetime(
        dated["DisplayStart"], errors="coerce"
    )
    dated["DisplayFinish"] = pd.to_datetime(
        dated["DisplayFinish"], errors="coerce"
    )
    dated = dated.dropna(subset=["DisplayStart", "DisplayFinish"])
    dated["Assignment"] = dated.apply(
        lambda row: (
            f"{row.get('TaskName') or row.get('TaskID')} | "
            f"{row.get('ProjectID')}"
        ),
        axis=1,
    )
    fallback_count = int(
        person.get("DateSource", pd.Series(dtype=str))
        .astype(str).ne("Assignment dates").sum()
    )
    metric_columns = st.columns(4)
    metric_columns[0].metric("Assignments", len(person))
    metric_columns[1].metric(
        "Projects",
        person["ProjectID"].dropna().astype(str).nunique(),
    )
    metric_columns[2].metric(
        "Conflict assignments",
        int(person["ConflictStatus"].ne("Green").sum()),
    )
    metric_columns[3].metric("Date fallbacks", fallback_count)

    if dated.empty:
        st.info("No complete dates are available for this person's work.")
    else:
        timeline = (
            alt.Chart(dated)
            .mark_bar(cornerRadius=3)
            .encode(
                x=alt.X("DisplayStart:T", title="Date"),
                x2=alt.X2("DisplayFinish:T"),
                y=alt.Y(
                    "Assignment:N",
                    sort=alt.SortField("DisplayStart"),
                    title=None,
                ),
                color=alt.Color(
                    "ConflictStatus:N",
                    title="Conflict status",
                    scale=alt.Scale(
                        domain=["Green", "Amber", "Red"],
                        range=["#2e7d32", "#f9a825", "#c62828"],
                    ),
                ),
                tooltip=[
                    alt.Tooltip("TaskName:N", title="Task"),
                    alt.Tooltip("TaskID:N", title="Task ID"),
                    alt.Tooltip("ProjectID:N", title="Project"),
                    alt.Tooltip(
                        "ConflictStatus:N", title="Conflict status"
                    ),
                    alt.Tooltip(
                        "PeakConflictAllocationPct:Q",
                        title="Peak overlapping allocation (%)",
                    ),
                    alt.Tooltip("AllocationPct:Q", title="Allocation (%)"),
                    alt.Tooltip("DisplayStart:T", title="Start"),
                    alt.Tooltip("DisplayFinish:T", title="Finish"),
                    alt.Tooltip("DateSource:N", title="Date source"),
                ],
            )
        )
        st.altair_chart(timeline, width="stretch")
    st.caption(
        "Green means no calculated conflict; Amber means a conflict below "
        f"the configured high threshold; Red means "
        f"{metrics.get('conflict_red_threshold_pct', 130)}% or more. "
        "Assignment dates take precedence. Missing start or finish dates "
        "fall back to the task forecast and remain labelled in the evidence."
    )

    st.subheader("Assignments for this person")
    person_fields = [
        column for column in (
            "ProjectID", "TaskName", "TaskID", "AllocationPct",
            "DisplayStart", "DisplayFinish", "DateSource",
            "ConflictStatus", "PeakConflictAllocationPct",
            "ConflictPeriodCount",
        )
        if column in person
    ]
    st.dataframe(
        person[person_fields],
        hide_index=True,
        width="stretch",
    )

    st.subheader("Conflict periods for this person")
    if person_conflicts.empty:
        st.info("No over-allocation conflict periods were identified.")
    else:
        st.dataframe(
            person_conflicts,
            hide_index=True,
            width="stretch",
        )


def _project_view(
    project_summary,
    resource_summary,
    unassigned_work,
    snapshot_id,
):
    st.subheader("Compare projects")
    st.caption(
        "Compare projects using one saved resource measure at a time, then "
        "inspect the people and unassigned work behind a selected project."
    )
    if project_summary.empty:
        st.info("No project resource evidence is available.")
        return

    measures = {
        "Assignment coverage": "AssignmentCoveragePct",
        "People": "ResourceCount",
        "Shared people": "SharedResourceCount",
        "People with conflicts": "ConflictResourceCount",
        "Conflict periods": "ConflictPeriodCount",
        "Unassigned tasks": "UnassignedTaskCount",
    }
    available = {
        label: column for label, column in measures.items()
        if column in project_summary
    }
    selected_measure = st.selectbox(
        "Comparison measure",
        list(available),
        key=f"resource_project_measure_{snapshot_id}",
    )
    measure_column = available[selected_measure]
    comparison = project_summary.copy()
    comparison[measure_column] = pd.to_numeric(
        comparison[measure_column], errors="coerce"
    )
    chart = (
        alt.Chart(comparison)
        .mark_bar(color="#46637f")
        .encode(
            x=alt.X(f"{measure_column}:Q", title=selected_measure),
            y=alt.Y("ProjectID:N", sort="-x", title="Project"),
            tooltip=[
                alt.Tooltip("ProjectID:N", title="Project"),
                alt.Tooltip(
                    f"{measure_column}:Q", title=selected_measure
                ),
            ],
        )
    )
    st.altair_chart(chart, width="stretch")

    project_fields = [
        column for column in (
            "ProjectID", "TaskCount", "AssignedTaskCount",
            "UnassignedTaskCount", "AssignmentCoveragePct",
            "ResourceCount", "SharedResourceCount",
            "ConflictResourceCount", "ConflictPeriodCount",
        )
        if column in project_summary
    ]
    st.dataframe(
        project_summary[project_fields],
        hide_index=True,
        width="stretch",
    )

    project_ids = sorted(
        project_summary["ProjectID"].dropna().astype(str).unique()
    )
    selected_project = st.selectbox(
        "Project detail",
        project_ids,
        key=f"resource_project_{snapshot_id}",
    )
    involved = resource_summary[
        _contains_identifier(
            resource_summary.get(
                "ProjectIDs",
                pd.Series("", index=resource_summary.index),
            ),
            selected_project,
        )
    ]
    project_unassigned = unassigned_work[
        unassigned_work.get(
            "ProjectID",
            pd.Series("", index=unassigned_work.index),
        ).astype(str) == selected_project
    ]
    detail_columns = st.columns(2)
    with detail_columns[0]:
        st.subheader("People involved")
        if involved.empty:
            st.info("No assigned people are recorded for this project.")
        else:
            fields = [
                column for column in (
                    "ResourceName", "ResourceID", "Role", "Team",
                    "ProjectCount", "CrossProject",
                    "PeakConcurrentAllocationPct", "ConflictPeriodCount",
                )
                if column in involved
            ]
            st.dataframe(
                involved[fields],
                hide_index=True,
                width="stretch",
            )
    with detail_columns[1]:
        st.subheader("Unassigned work")
        if project_unassigned.empty:
            st.info("No unassigned tasks exist for this project.")
        else:
            st.dataframe(
                project_unassigned,
                hide_index=True,
                width="stretch",
            )


_, catalogue, client_id, snapshot = console_context()

render_hero(
    "Point-in-time diagnostic",
    "Resource lens",
    "Inspect allocation pressure, cross-project contention, assignment "
    "concentration and evidence coverage without inferring actual utilisation.",
    icon=":material/groups:",
)

if not snapshot:
    st.info("No diagnosed observation is available.")
    st.stop()

snapshot_id = snapshot["snapshot_id"]
bundle = catalogue.snapshot_bundle(snapshot_id, client_id)
outcome = diagnostic_outcome(bundle["diagnosis"], "resource")
if not outcome or outcome.get("status") != "success":
    st.info(
        "The resource lens is unavailable for this observation. Run a current "
        "resource diagnosis or review its capability fitness."
    )
    st.stop()

try:
    resource_summary = _read_product(
        catalogue, outcome, "resource_summary"
    )
    project_summary = _read_product(
        catalogue, outcome, "project_summary"
    )
    conflicts = _read_product(catalogue, outcome, "conflicts")
    unassigned_work = _read_product(
        catalogue, outcome, "unassigned_work"
    )
    timeline_reference = product_reference(
        outcome, "assignment_timeline"
    )
    assignment_timeline = (
        catalogue.read_table(timeline_reference)
        if timeline_reference else pd.DataFrame()
    )
except (FileNotFoundError, ValueError, MetadataReadError) as error:
    st.warning(f"Resource lens evidence is unavailable: {error}")
    st.stop()

metrics = outcome.get("metrics", {})
render_metric_row([
    ("Resources", metrics.get("resources_analysed")),
    ("Cross-project resources", metrics.get("cross_project_resources")),
    ("Conflict resources", metrics.get("conflict_resource_count")),
    ("Conflict periods", metrics.get("conflict_count")),
    (
        "Task assignment coverage",
        _percent(metrics.get("task_assignment_coverage_pct")),
    ),
])

view = st.segmented_control(
    "Resource perspective",
    ["Summary", "By person", "By project"],
    default="Summary",
    key=f"resource_view_{snapshot_id}",
)
if view == "By person":
    _person_view(
        resource_summary,
        assignment_timeline,
        conflicts,
        snapshot_id,
        metrics,
    )
elif view == "By project":
    _project_view(
        project_summary,
        resource_summary,
        unassigned_work,
        snapshot_id,
    )
else:
    _summary_view(resource_summary, conflicts, metrics)

with st.expander("Evidence limits"):
    st.write(metrics.get(
        "capacity_assumption",
        "The configured conflict threshold is applied to concurrent "
        "assignment allocation.",
    ))
    st.write(
        "Assignment-date coverage: "
        f"{_percent(metrics.get('assignment_date_coverage_pct'))}; "
        "resource-capacity coverage: "
        f"{_percent(metrics.get('resource_capacity_coverage_pct'))}."
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
        "Allocation percentages are planned assignment evidence. They are "
        "not timesheets, actual effort, or a forecast of remaining capacity."
    )
