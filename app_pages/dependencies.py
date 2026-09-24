"""Read-only dependency lens for one diagnosed observation."""

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from components.console import render_hero, render_metric_row
from services.console_context import console_context
from services.lenses import diagnostic_outcome, product_reference
from services.platform_reader import MetadataReadError


def _read_product(catalogue, outcome, name):
    reference = product_reference(outcome, name)
    if not reference:
        raise ValueError(f"Dependency product {name!r} is not recorded")
    return catalogue.read_table(reference)


_, catalogue, client_id, snapshot = console_context()

render_hero(
    "Point-in-time diagnostic",
    "Dependency lens",
    "Inspect dependency coverage, cross-project coupling, connectivity hubs, "
    "bridges, articulation points and cycles from saved graph evidence.",
    icon=":material/account_tree:",
)

if not snapshot:
    st.info("No diagnosed observation is available.")
    st.stop()

snapshot_id = snapshot["snapshot_id"]
bundle = catalogue.snapshot_bundle(snapshot_id, client_id)
outcome = diagnostic_outcome(bundle["diagnosis"], "dependency")
if not outcome or outcome.get("status") != "success":
    st.info(
        "The dependency lens is unavailable for this observation. Run a "
        "current dependency diagnosis or review its capability fitness."
    )
    st.stop()

try:
    edges = _read_product(catalogue, outcome, "edges")
    tasks = _read_product(catalogue, outcome, "task_connectivity")
    projects = _read_product(catalogue, outcome, "project_summary")
except (FileNotFoundError, ValueError, MetadataReadError) as error:
    st.warning(f"Dependency lens evidence is unavailable: {error}")
    st.stop()

metrics = outcome.get("metrics", {})
render_metric_row([
    ("Dependencies", metrics.get("dependencies_analysed")),
    ("Linked-task coverage", (
        f"{metrics.get('dependency_coverage_pct')}%"
        if metrics.get("dependency_coverage_pct") is not None
        else "Unavailable"
    )),
    ("Cross-project links", metrics.get("cross_project_dependencies")),
    ("Hub tasks", metrics.get("hub_tasks")),
    ("Cycle tasks", metrics.get("cycle_tasks")),
])

filters = st.columns(2)
project_ids = sorted(
    projects.get("ProjectID", pd.Series(dtype=str))
    .dropna().astype(str).unique().tolist()
)
selected_project = filters[0].selectbox(
    "Project",
    [None, *project_ids],
    format_func=lambda value: "All projects" if value is None else value,
    key=f"dependency_project_{snapshot_id}",
)
relationship_types = sorted(
    value for value in edges.get(
        "RelationshipType", pd.Series(dtype=str)
    ).dropna().astype(str).unique().tolist() if value
)
selected_relationships = filters[1].pills(
    "Relationship type",
    relationship_types,
    selection_mode="multi",
    key=f"dependency_relationship_{snapshot_id}",
)

visible_edges = edges.copy()
visible_tasks = tasks.copy()
visible_projects = projects.copy()
if selected_project is not None:
    visible_edges = visible_edges[
        (visible_edges["PredecessorProjectID"].astype(str) == selected_project)
        | (visible_edges["SuccessorProjectID"].astype(str) == selected_project)
    ]
    visible_tasks = visible_tasks[
        visible_tasks["ProjectID"].astype(str) == selected_project
    ]
    visible_projects = visible_projects[
        visible_projects["ProjectID"].astype(str) == selected_project
    ]
if selected_relationships:
    visible_edges = visible_edges[
        visible_edges["RelationshipType"].isin(selected_relationships)
    ]

st.subheader("Dependency network")
st.caption(
    "Shows how tasks depend on one another. Lines are dependencies and larger "
    "circles have more connections. Cross-project links, hubs, bridges and "
    "cycles are prompts for investigation, not proof of delivery risk."
)
if visible_tasks.empty:
    st.info("No task nodes match the selected filters.")
else:
    edge_chart = (
        alt.Chart(visible_edges)
        .mark_rule(opacity=0.45)
        .encode(
            x=alt.X("PredecessorX:Q", axis=None),
            x2="SuccessorX:Q",
            y=alt.Y("PredecessorY:Q", axis=None),
            y2="SuccessorY:Q",
            color=alt.condition(
                "datum.CrossProject",
                alt.value("#b94a48"),
                alt.value("#8a98a6"),
            ),
            tooltip=[
                "PredecessorTaskID:N", "SuccessorTaskID:N",
                "RelationshipType:N", "CrossProject:N",
                "IsBridge:N", "InCycle:N",
            ],
        )
    )
    node_chart = (
        alt.Chart(visible_tasks)
        .mark_circle(opacity=0.9, stroke="white", strokeWidth=1)
        .encode(
            x=alt.X("NetworkX:Q", axis=None),
            y=alt.Y("NetworkY:Q", axis=None),
            size=alt.Size(
                "ConnectivityDegree:Q",
                scale=alt.Scale(range=[80, 900]),
                title="Connections",
            ),
            color=alt.Color("ProjectID:N", title="Project"),
            tooltip=[
                "TaskName:N", "TaskID:N", "ProjectID:N",
                "PredecessorCount:Q", "SuccessorCount:Q",
                "ConnectivityDegree:Q", "IsArticulation:N",
                "InCycle:N",
            ],
        )
    )
    st.altair_chart(edge_chart + node_chart, width="stretch")
    st.caption(
        "The circular coordinates are saved by DataPlatform for a stable "
        "inspection view; node size represents saved connectivity degree."
    )

coverage_column, connectivity_column = st.columns(2)
with coverage_column:
    st.subheader("Project dependency coverage")
    if visible_projects.empty:
        st.info("No project coverage records match the selected filters.")
    else:
        st.bar_chart(
            visible_projects,
            x="ProjectID",
            y="DependencyCoveragePct",
            width="stretch",
        )
with connectivity_column:
    st.subheader("Most connected tasks")
    connected = visible_tasks[
        visible_tasks["ConnectivityDegree"] > 0
    ].head(20)
    if connected.empty:
        st.info("No connected tasks are available in this scope.")
    else:
        st.dataframe(
            connected[[
                "TaskName", "TaskID", "ProjectID", "ConnectivityDegree",
                "CrossProjectDependencyCount", "IsHub",
                "IsArticulation", "InCycle",
            ]],
            hide_index=True,
            width="stretch",
        )

st.subheader("Dependency evidence")
edge_columns = [
    "DependencyID", "PredecessorTaskID", "PredecessorProjectID",
    "SuccessorTaskID", "SuccessorProjectID", "RelationshipType",
    "LagDays", "CrossProject", "IsBridge", "InCycle",
]
if visible_edges.empty:
    st.info("No dependency links match the selected filters.")
else:
    st.dataframe(
        visible_edges[edge_columns],
        hide_index=True,
        width="stretch",
    )

with st.expander("Method and limits"):
    st.caption(
        "Bridge and articulation labels use the undirected structure of the "
        "saved dependency graph. Cycle evidence uses directed links. These "
        "are structural observations, not claims that an item will fail."
    )
    st.caption(
        "Unlinked tasks may be legitimate schedule starts, finishes or "
        "summary activities; coverage is not independently classified as "
        "good or bad."
    )
