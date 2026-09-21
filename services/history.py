"""Presentation transforms for governed historical project trend products."""

from __future__ import annotations

from typing import Any, Mapping

import pandas as pd


OBSERVATION_COLUMNS = {
    "ObservationIndex",
    "SnapshotID",
    "ObservationDate",
    "ProjectID",
    "ProjectName",
    "FinishDate",
    "Status",
}
SUMMARY_COLUMNS = {
    "ProjectID",
    "FinishDateMovementCount",
    "FinishDateSlippageCount",
    "TotalDaysSlipped",
    "StatusMovementCount",
    "UnavailableAdjacentTransitions",
}
SUMMARY_NUMERIC_COLUMNS = SUMMARY_COLUMNS.difference({"ProjectID"})


def _required_columns(frame: pd.DataFrame, required: set[str], name: str) -> None:
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(
            f"Governed {name} evidence is missing required columns: "
            + ", ".join(missing)
        )


def _signed_days(value: Any) -> str:
    number = int(value)
    return f"{number:+d}d" if number else "0d"


def prepare_delivery_trajectory(
    observations: pd.DataFrame,
    summary: pd.DataFrame,
) -> tuple[pd.DataFrame, int]:
    """Return chart-ready observations without bridging continuity gaps."""

    _required_columns(observations, OBSERVATION_COLUMNS, "observation history")
    _required_columns(summary, SUMMARY_COLUMNS, "trend summary")

    frame = observations.copy()
    frame["ObservationIndex"] = pd.to_numeric(
        frame["ObservationIndex"], errors="coerce"
    )
    frame["ObservationDate"] = pd.to_datetime(
        frame["ObservationDate"], errors="coerce"
    )
    frame["FinishDate"] = pd.to_datetime(frame["FinishDate"], errors="coerce")
    frame["ProjectID"] = frame["ProjectID"].astype("string").str.strip()

    valid = (
        frame["ObservationIndex"].notna()
        & frame["ObservationDate"].notna()
        & frame["FinishDate"].notna()
        & frame["ProjectID"].notna()
        & frame["ProjectID"].ne("")
    )
    excluded_count = int((~valid).sum())
    frame = frame.loc[valid].copy()
    if frame.empty:
        return frame, excluded_count

    frame["ProjectName"] = (
        frame["ProjectName"].fillna("").astype(str).str.strip()
    )
    frame.loc[frame["ProjectName"].eq(""), "ProjectName"] = frame["ProjectID"]
    frame["Status"] = (
        frame["Status"]
        .fillna("Unknown")
        .astype(str)
        .str.strip()
        .replace("", "Unknown")
    )
    frame["Status"] = frame["Status"].str.title()
    frame = frame.sort_values(
        ["ProjectID", "ObservationIndex", "ObservationDate"]
    ).reset_index(drop=True)

    index_gap = frame.groupby("ProjectID")["ObservationIndex"].diff().ne(1)
    frame["ContinuitySegment"] = index_gap.groupby(frame["ProjectID"]).cumsum()
    frame["TrajectorySeries"] = (
        frame["ProjectID"].astype(str)
        + "::"
        + frame["ContinuitySegment"].astype(str)
    )
    segment = frame.groupby("TrajectorySeries", sort=False)
    segment_start = segment["FinishDate"].transform("first")
    frame["CumulativeMovementDays"] = (
        frame["FinishDate"] - segment_start
    ).dt.days.astype(int)
    frame["PeriodMovementDays"] = segment["FinishDate"].diff().dt.days

    prepared_summary = summary[list(SUMMARY_COLUMNS)].copy()
    prepared_summary["ProjectID"] = (
        prepared_summary["ProjectID"].astype("string").str.strip()
    )
    for column in SUMMARY_NUMERIC_COLUMNS:
        prepared_summary[column] = pd.to_numeric(
            prepared_summary[column], errors="coerce"
        ).fillna(0).astype(int)
    prepared_summary = prepared_summary.drop_duplicates(
        subset=["ProjectID"], keep="last"
    )
    frame = frame.merge(prepared_summary, on="ProjectID", how="left")
    for column in SUMMARY_NUMERIC_COLUMNS:
        frame[column] = frame[column].fillna(0).astype(int)

    frame["HadFinishMovement"] = frame["FinishDateMovementCount"].gt(0)
    frame["DisplayName"] = frame.apply(
        lambda row: f"{row['ProjectName']} · {row['ProjectID']}", axis=1
    )
    latest_indices = frame.groupby("ProjectID")["ObservationIndex"].transform(
        "max"
    )
    frame["IsLatest"] = frame["ObservationIndex"].eq(latest_indices)
    frame["EndLabel"] = ""
    frame.loc[frame["IsLatest"], "EndLabel"] = frame.loc[
        frame["IsLatest"]
    ].apply(
        lambda row: (
            f"{row['ProjectID']} "
            f"{_signed_days(row['CumulativeMovementDays'])}"
        ),
        axis=1,
    )
    return frame, excluded_count


def delivery_trajectory_metrics(summary: pd.DataFrame) -> dict[str, int]:
    """Return display metrics already established by the governed summary."""

    _required_columns(summary, SUMMARY_COLUMNS, "trend summary")
    numeric = summary.copy()
    for column in SUMMARY_NUMERIC_COLUMNS:
        numeric[column] = pd.to_numeric(
            numeric[column], errors="coerce"
        ).fillna(0)
    return {
        "projects_moved": int(
            numeric["FinishDateMovementCount"].gt(0).sum()
        ),
        "projects_slipped": int(
            numeric["FinishDateSlippageCount"].gt(0).sum()
        ),
        "total_days_slipped": int(numeric["TotalDaysSlipped"].sum()),
        "status_changes": int(numeric["StatusMovementCount"].sum()),
    }


def scope_delivery_trajectory(
    trajectory: pd.DataFrame,
    movers_only: bool,
) -> pd.DataFrame:
    """Filter a prepared trajectory to governed forecast movers."""

    if trajectory.empty or not movers_only:
        return trajectory.copy()
    return trajectory.loc[trajectory["HadFinishMovement"]].copy()


def delivery_project_facts(
    trajectory: pd.DataFrame,
    project_id: str,
) -> dict[str, Any] | None:
    """Return factual display values for one selected project trajectory."""

    project = trajectory.loc[
        trajectory["ProjectID"].astype(str).eq(str(project_id))
    ].sort_values(["ObservationIndex", "ObservationDate"])
    if project.empty:
        return None
    latest = project.iloc[-1]
    latest_segment = project.loc[
        project["TrajectorySeries"].eq(latest["TrajectorySeries"])
    ]
    first = latest_segment.iloc[0]
    return {
        "project_id": str(latest["ProjectID"]),
        "project_name": str(latest["ProjectName"]),
        "net_movement_days": int(latest["CumulativeMovementDays"]),
        "slippage_transitions": int(latest["FinishDateSlippageCount"]),
        "latest_finish": latest["FinishDate"],
        "status_path": f"{first['Status']} → {latest['Status']}",
        "unavailable_transitions": int(
            latest["UnavailableAdjacentTransitions"]
        ),
    }


def selected_trajectory_project_id(event: Any) -> str | None:
    """Extract a project identifier from a Streamlit Vega selection event."""

    if not event:
        return None
    try:
        selected = event.get("selection", {}).get("trajectory_pick")
    except AttributeError:
        return None
    if isinstance(selected, list) and selected:
        first = selected[0]
        if isinstance(first, Mapping):
            value = first.get("ProjectID")
            return str(value) if value else None
    if isinstance(selected, Mapping):
        value = selected.get("ProjectID")
        return str(value) if value else None
    return None
