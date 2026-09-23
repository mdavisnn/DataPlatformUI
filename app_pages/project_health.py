"""Read-only project comparison across deterministic diagnostic lenses."""

import pandas as pd
import streamlit as st

from components.console import render_finding, render_hero, render_metric_row
from services.console_context import console_context
from services.platform_reader import MetadataReadError


LENS_COLUMNS = [
    "PortfolioStatus",
    "ScheduleStatus",
    "ResourceStatus",
    "ReportingStatus",
    "DependencyStatus",
]

_, catalogue, client_id, snapshot = console_context()

render_hero(
    "Point-in-time diagnostic",
    "Project health",
    "Compare projects across separate analytical lenses, then inspect the "
    "governed Findings behind any highlighted condition.",
    icon=":material/grid_view:",
)

if not snapshot:
    st.info("No diagnosed observation is available.")
    st.stop()

bundle = catalogue.snapshot_bundle(snapshot["snapshot_id"], client_id)
reference = bundle["diagnosis"].get("project_health_object")
if not reference:
    st.warning(
        "This observation predates the project-health contract. Re-run "
        "diagnosis to create the governed matrix.",
        icon=":material/history:",
    )
    st.stop()

try:
    matrix = catalogue.read_table(reference)
except (FileNotFoundError, ValueError, MetadataReadError) as error:
    st.warning(f"Project health evidence is unavailable: {error}")
    st.stop()

if matrix.empty:
    st.info("The selected observation contains no canonical projects.")
    st.stop()

required = {"ProjectID", "ProjectName", "FindingCount", *LENS_COLUMNS}
if not required.issubset(matrix.columns):
    st.error("The project-health artifact is incompatible with this UI.")
    st.stop()

status_options = [
    status for status in (
        "Significant", "Attention", "No finding", "Not assessed"
    )
    if matrix[LENS_COLUMNS].isin([status]).any().any()
]
with st.container(horizontal=True):
    portfolios = sorted(
        value for value in matrix.get(
            "PortfolioID", pd.Series(dtype="object")
        ).dropna().astype(str).unique() if value
    )
    selected_portfolios = st.multiselect(
        "Portfolio",
        portfolios,
        key=f"health_portfolios_{snapshot['snapshot_id']}",
    )
    selected_statuses = st.pills(
        "Lens status",
        status_options,
        selection_mode="multi",
        key=f"health_status_{snapshot['snapshot_id']}",
    )

filtered = matrix
if selected_portfolios:
    filtered = filtered[
        filtered["PortfolioID"].astype(str).isin(selected_portfolios)
    ]
if selected_statuses:
    filtered = filtered[
        filtered[LENS_COLUMNS].isin(selected_statuses).any(axis=1)
    ]

render_metric_row([
    ("Projects shown", len(filtered)),
    ("With findings", int((filtered["FindingCount"] > 0).sum())),
    (
        "Significant projects",
        int(filtered[LENS_COLUMNS].eq("Significant").any(axis=1).sum()),
    ),
    (
        "Not assessed",
        int(filtered[LENS_COLUMNS].eq("Not assessed").any(axis=1).sum()),
    ),
])

display_columns = [
    column for column in (
        "ProjectName", "ProjectID", "PortfolioID", "ProgrammeID",
        "RAGStatus", "TaskCount", *LENS_COLUMNS, "DataFitness",
        "FindingCount",
    )
    if column in filtered
]
st.dataframe(
    filtered[display_columns],
    hide_index=True,
    column_config={
        "ProjectName": st.column_config.TextColumn(
            "Project", pinned=True
        ),
        "FindingCount": st.column_config.NumberColumn(
            "Findings", format="%d"
        ),
        "TaskCount": st.column_config.NumberColumn(
            "Activities", format="%d"
        ),
    },
)
st.caption(
    "No finding means the capability ran without producing a Finding for "
    "that project; it is not a general assertion of project health."
)

if filtered.empty:
    st.info("No projects match the selected filters.")
    st.stop()

labels = {
    str(row.ProjectID): (
        f"{row.ProjectName} | {row.ProjectID}"
        if str(row.ProjectName) else str(row.ProjectID)
    )
    for row in filtered[["ProjectID", "ProjectName"]].itertuples(index=False)
}
project_id = st.selectbox(
    "Inspect project",
    list(labels),
    format_func=labels.get,
    key=f"health_project_{snapshot['snapshot_id']}",
)
project = filtered[
    filtered["ProjectID"].astype(str) == str(project_id)
].iloc[0]

st.subheader(labels[str(project_id)])
status_table = {
    column.replace("Status", ""): project[column]
    for column in LENS_COLUMNS
}
status_table["Data fitness"] = project.get("DataFitness", "Unknown")
st.table(status_table, border="horizontal", width="content")

finding_ids = {
    value for value in str(project.get("FindingIDs", "")).split("|")
    if value and value.lower() != "nan"
}
project_findings = [
    finding for finding in bundle["findings"].get("findings", [])
    if str(finding.get("finding_id", "")) in finding_ids
]
st.subheader("Project findings")
if not project_findings:
    st.info("No deterministic Findings affect this project.")
for finding in project_findings:
    render_finding(finding)
