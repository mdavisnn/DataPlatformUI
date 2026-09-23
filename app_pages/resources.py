"""Read-only resource lens over one diagnosed canonical observation."""

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
        raise ValueError(f"Resource product {name!r} is not recorded")
    return catalogue.read_table(reference)


def _contains_identifier(values: pd.Series, identifier: str) -> pd.Series:
    return values.fillna("").astype(str).map(
        lambda value: identifier in {
            item.strip() for item in value.split(",") if item.strip()
        }
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

filter_columns = st.columns(2)
resource_ids = sorted(
    resource_summary.get("ResourceID", pd.Series(dtype=str))
    .dropna().astype(str).unique().tolist()
)
resource_names = {
    str(row.ResourceID): (
        f"{row.ResourceName} | {row.ResourceID}"
        if str(row.ResourceName).strip() else str(row.ResourceID)
    )
    for row in resource_summary[
        ["ResourceID", "ResourceName"]
    ].itertuples(index=False)
}
selected_resource = filter_columns[0].selectbox(
    "Resource",
    [None, *resource_ids],
    format_func=lambda value: (
        "All resources"
        if value is None else resource_names.get(value, value)
    ),
    key=f"resource_person_{snapshot_id}",
)
project_ids = sorted(
    project_summary.get("ProjectID", pd.Series(dtype=str))
    .dropna().astype(str).unique().tolist()
)
selected_project = filter_columns[1].selectbox(
    "Project",
    [None, *project_ids],
    format_func=lambda value: "All projects" if value is None else value,
    key=f"resource_project_{snapshot_id}",
)

filtered_resources = resource_summary.copy()
filtered_projects = project_summary.copy()
filtered_conflicts = conflicts.copy()
filtered_unassigned = unassigned_work.copy()
if selected_resource is not None:
    filtered_resources = filtered_resources[
        filtered_resources["ResourceID"].astype(str) == selected_resource
    ]
    if not filtered_conflicts.empty:
        filtered_conflicts = filtered_conflicts[
            filtered_conflicts["ResourceID"].astype(str) == selected_resource
        ]
if selected_project is not None:
    filtered_projects = filtered_projects[
        filtered_projects["ProjectID"].astype(str) == selected_project
    ]
    filtered_unassigned = filtered_unassigned[
        filtered_unassigned["ProjectID"].astype(str) == selected_project
    ]
    if not filtered_conflicts.empty:
        filtered_conflicts = filtered_conflicts[
            _contains_identifier(
                filtered_conflicts["ProjectIDs"], selected_project
            )
        ]
    if selected_resource is None and "ProjectIDs" in filtered_resources:
        filtered_resources = filtered_resources[
            _contains_identifier(
                filtered_resources["ProjectIDs"], selected_project
            )
        ]

st.subheader("Allocation pressure")
pressure = filtered_resources.copy()
pressure["PeakConcurrentAllocationPct"] = pd.to_numeric(
    pressure.get("PeakConcurrentAllocationPct"), errors="coerce"
)
pressure = pressure.dropna(subset=["PeakConcurrentAllocationPct"]).head(25)
if pressure.empty:
    st.info("No dated allocation pressure evidence is available in this scope.")
else:
    pressure["Resource"] = pressure.apply(
        lambda row: str(row.get("ResourceName") or row.get("ResourceID")),
        axis=1,
    )
    bars = (
        alt.Chart(pressure)
        .mark_bar(color="#46637f")
        .encode(
            x=alt.X(
                "PeakConcurrentAllocationPct:Q",
                title="Peak concurrent assignment allocation (%)",
            ),
            y=alt.Y(
                "Resource:N",
                sort="-x",
                title=None,
            ),
            tooltip=[
                alt.Tooltip("Resource:N"),
                alt.Tooltip(
                    "PeakConcurrentAllocationPct:Q",
                    title="Peak allocation",
                ),
                alt.Tooltip("ProjectCount:Q", title="Projects"),
                alt.Tooltip(
                    "ConflictPeriodCount:Q", title="Conflict periods"
                ),
            ],
        )
    )
    threshold = alt.Chart(pd.DataFrame({
        "Threshold": [metrics.get("conflict_threshold_pct", 100)]
    })).mark_rule(color="#b94a48", strokeDash=[5, 4]).encode(
        x="Threshold:Q"
    )
    st.altair_chart(bars + threshold, width="stretch")

st.subheader("Resource concentration and cross-project usage")
resource_fields = [
    column for column in (
        "ResourceName", "ResourceID", "Role", "Team", "CapacityPct",
        "AssignmentCount", "TaskCount", "ProjectCount", "CrossProject",
        "AssignmentAllocationSharePct", "PeakConcurrentAllocationPct",
        "ConflictPeriodCount", "AssignmentDateCoveragePct",
    )
    if column in filtered_resources
]
if filtered_resources.empty:
    st.info("No resources match the selected filters.")
else:
    st.dataframe(
        filtered_resources[resource_fields],
        hide_index=True,
        width="stretch",
    )

st.subheader("Conflict periods")
conflict_fields = [
    column for column in (
        "ResourceName", "ResourceID", "ConflictStart", "ConflictFinish",
        "TotalAllocation", "OverAllocation", "ProjectCount", "TaskCount",
        "ProjectIDs", "TaskIDs",
    )
    if column in filtered_conflicts
]
if filtered_conflicts.empty:
    st.info("No over-allocation conflict periods exist in this scope.")
else:
    st.dataframe(
        filtered_conflicts[conflict_fields],
        hide_index=True,
        width="stretch",
    )

st.subheader("Project assignment coverage")
project_fields = [
    column for column in (
        "ProjectID", "TaskCount", "AssignedTaskCount",
        "UnassignedTaskCount", "AssignmentCoveragePct", "ResourceCount",
        "SharedResourceCount", "ConflictResourceCount",
        "ConflictPeriodCount",
    )
    if column in filtered_projects
]
st.dataframe(
    filtered_projects[project_fields],
    hide_index=True,
    width="stretch",
)

with st.expander(
    f"Unassigned work ({len(filtered_unassigned)})",
    expanded=not filtered_unassigned.empty,
):
    if filtered_unassigned.empty:
        st.info("No unassigned tasks exist in this scope.")
    else:
        st.dataframe(
            filtered_unassigned,
            hide_index=True,
            width="stretch",
        )

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
