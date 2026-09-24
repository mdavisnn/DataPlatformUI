"""Presentation models for governed project-profile evidence."""

from __future__ import annotations

from typing import Any

import pandas as pd


ATTENTION_METRICS = {
    "schedule_condition_task_pct": "ScheduleConditionPct",
    "conflict_resource_pct": "ConflictResourcePct",
    "average_dependency_connectivity": "AverageConnectivity",
}
PROFILE_COLUMNS = {
    "ProjectID", "ProjectName", "Domain", "MetricID", "MetricLabel",
    "Value", "Unit", "PercentileRank", "PopulationCount", "Median",
    "OutsideIqr", "Availability", "AvailabilityReason",
}


def _require_columns(frame: pd.DataFrame, required: set[str], name: str) -> None:
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(
            f"{name} is missing required columns: {sorted(missing)}"
        )


def _finding_status(row: pd.Series) -> str:
    counts = {
        severity: pd.to_numeric(row.get(column), errors="coerce")
        for severity, column in {
            "high": "HighFindings",
            "medium": "MediumFindings",
            "low": "LowFindings",
        }.items()
    }
    counts = {
        severity: 0 if pd.isna(value) else float(value)
        for severity, value in counts.items()
    }
    if counts["high"] > 0:
        return "Significant"
    if counts["medium"] > 0 or counts["low"] > 0:
        return "Attention"
    return "No finding"


def prepare_attention_map(
    profile: pd.DataFrame,
    project_health: pd.DataFrame,
) -> pd.DataFrame:
    """Return one plotting row per project from governed saved measures."""

    _require_columns(profile, PROFILE_COLUMNS, "Project profile")
    _require_columns(
        project_health,
        {
            "ProjectID", "ProjectName", "RAGStatus", "DataFitness",
            "FindingCount", "HighFindings", "MediumFindings", "LowFindings",
        },
        "Project health",
    )
    selected = profile[profile["MetricID"].isin(ATTENTION_METRICS)].copy()
    selected["Value"] = pd.to_numeric(selected["Value"], errors="coerce")
    available = selected["Availability"].eq("Available")
    selected.loc[~available, "Value"] = pd.NA
    medians = (
        selected.dropna(subset=["Median"])
        .drop_duplicates("MetricID")
        .set_index("MetricID")["Median"]
    )
    values = selected.pivot_table(
        index="ProjectID",
        columns="MetricID",
        values="Value",
        aggfunc="first",
        dropna=False,
    ).rename(columns=ATTENTION_METRICS).reset_index()
    for column in ATTENTION_METRICS.values():
        if column not in values:
            values[column] = pd.NA
    result = project_health.merge(values, on="ProjectID", how="left")
    result["FindingStatus"] = result.apply(_finding_status, axis=1)
    result["ProjectLabel"] = result.apply(
        lambda row: (
            f"{row['ProjectName']} | {row['ProjectID']}"
            if str(row.get("ProjectName", "")).strip()
            else str(row["ProjectID"])
        ),
        axis=1,
    )
    result["Plottable"] = (
        result["ScheduleConditionPct"].notna()
        & result["ConflictResourcePct"].notna()
    )
    result["DependencyEvidence"] = result["AverageConnectivity"].map(
        lambda value: "Available" if pd.notna(value) else "Unavailable"
    )
    result["ConnectivityBubble"] = (
        pd.to_numeric(result["AverageConnectivity"], errors="coerce")
        .fillna(0)
        .clip(lower=0)
        + 0.25
    )
    result["ScheduleMedian"] = pd.to_numeric(
        medians.get("schedule_condition_task_pct"), errors="coerce"
    )
    result["ResourceMedian"] = pd.to_numeric(
        medians.get("conflict_resource_pct"), errors="coerce"
    )
    return result.sort_values(
        ["Plottable", "HighFindings", "MediumFindings", "ProjectID"],
        ascending=[False, False, False, True],
    ).reset_index(drop=True)


def _value_label(value: Any, unit: str) -> str:
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return "Unavailable"
    rendered = f"{float(number):,.1f}".rstrip("0").rstrip(".")
    if unit == "%":
        return f"{rendered}%"
    return f"{rendered} {unit}".strip()


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes"}


def prepare_project_fingerprint(
    profile: pd.DataFrame,
    project_id: str,
) -> pd.DataFrame:
    """Prepare ordered measures for one project's percentile fingerprint."""

    _require_columns(profile, PROFILE_COLUMNS, "Project profile")
    result = profile[
        profile["ProjectID"].astype(str) == str(project_id)
    ].copy()
    if result.empty:
        raise ValueError(f"Project profile has no rows for {project_id}")
    result["Value"] = pd.to_numeric(result["Value"], errors="coerce")
    result["PercentileRank"] = pd.to_numeric(
        result["PercentileRank"], errors="coerce"
    )
    result["ValueLabel"] = result.apply(
        lambda row: _value_label(row.get("Value"), str(row.get("Unit", ""))),
        axis=1,
    )
    result["QuartileStart"] = 25.0
    result["QuartileEnd"] = 75.0
    result["PortfolioMedian"] = 50.0
    result["LabelPosition"] = 100.0
    result["Unusual"] = result["OutsideIqr"].fillna(False).map(
        lambda value: "Outside IQR" if _truthy(value) else "Within IQR"
    )
    return result.reset_index(drop=True)


def selected_attention_project(event: Any) -> str | None:
    """Extract the selected project ID from a Streamlit Altair event."""

    if event is None:
        return None
    selection = (
        event.get("selection", {})
        if isinstance(event, dict)
        else getattr(event, "selection", {})
    )
    points = (
        selection.get("project_select", [])
        if isinstance(selection, dict)
        else getattr(selection, "project_select", [])
    )
    if not points:
        return None
    point = points[0]
    value = point.get("ProjectID") if isinstance(point, dict) else None
    return str(value) if value not in (None, "") else None
