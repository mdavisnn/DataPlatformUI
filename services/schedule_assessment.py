"""Presentation-only preparation for governed DCMA assessment products."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pandas as pd


PROJECT_SUMMARY_COLUMNS = {
    "ProjectID",
    "ProjectName",
    "TaskCount",
    "EligibleActivityCount",
    "AssessableMetrics",
    "OutOfThresholdMetrics",
    "NotAssessableMetrics",
    "AssessmentStatus",
}
ASSESSMENT_COLUMNS = {
    "ProjectID",
    "ProjectName",
    "MetricNumber",
    "RuleID",
    "MetricName",
    "Status",
    "Value",
    "Unit",
    "Comparison",
    "Threshold",
    "EvidenceCoveragePct",
    "StatusDate",
    "StatusDateSource",
    "Population",
    "Reason",
    "WorkingDayBasis",
}
CONDITION_COLUMNS = {
    "RuleID",
    "MetricNumber",
    "MetricName",
    "ProjectID",
    "ProjectName",
    "EntityType",
    "EntityID",
    "Condition",
    "ObservedValue",
    "Threshold",
    "Message",
}
ACTIVITY_COLUMNS = {
    "ProjectID",
    "ProjectName",
    "TaskID",
    "TaskName",
    "BaselineDurationWorkingDays",
    "ForecastDurationDays",
    "IsMilestone",
}

STATUS_LABELS = {
    "outside_threshold": "Outside tripwire",
    "within_threshold": "Within threshold",
    "not_assessable": "Not assessable",
}
STATUS_DATE_SOURCE_LABELS = {
    "project_data_date": "Project data date",
    "snapshot_observation_date": "Observation date fallback",
}


def _require_columns(frame: pd.DataFrame, required: set[str], name: str) -> None:
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"{name} is missing required columns: {missing}")


def validate_dcma_products(
    project_summary: pd.DataFrame,
    assessment: pd.DataFrame,
    conditions: pd.DataFrame,
    activity_profile: pd.DataFrame,
) -> None:
    """Validate the four products required by the DCMA schedule view."""

    _require_columns(
        project_summary, PROJECT_SUMMARY_COLUMNS, "DCMA project summary"
    )
    _require_columns(assessment, ASSESSMENT_COLUMNS, "DCMA assessment")
    _require_columns(conditions, CONDITION_COLUMNS, "DCMA conditions")
    _require_columns(
        activity_profile, ACTIVITY_COLUMNS, "Schedule activity profile"
    )


def project_labels(project_summary: pd.DataFrame) -> dict[str, str]:
    """Return stable consultant-facing labels keyed by project ID."""

    labels: dict[str, str] = {}
    for row in project_summary[["ProjectID", "ProjectName"]].itertuples(
        index=False
    ):
        project_id = str(row.ProjectID)
        project_name = (
            "" if pd.isna(row.ProjectName) else str(row.ProjectName).strip()
        )
        labels[project_id] = (
            f"{project_name} | {project_id}" if project_name else project_id
        )
    return labels


def metric_labels(assessment: pd.DataFrame) -> dict[int, str]:
    """Return ordered labels keyed by DCMA metric number."""

    rows = (
        assessment[["MetricNumber", "MetricName"]]
        .drop_duplicates()
        .sort_values("MetricNumber")
    )
    return {
        int(row.MetricNumber): f"{int(row.MetricNumber):02d} · {row.MetricName}"
        for row in rows.itertuples(index=False)
    }


def filter_assessment(
    assessment: pd.DataFrame,
    *,
    project_id: str | None = None,
    metric_number: int | None = None,
    statuses: Iterable[str] = (),
) -> pd.DataFrame:
    """Filter saved assessment rows without recalculating their meaning."""

    result = assessment.copy()
    if project_id is not None:
        result = result[result["ProjectID"].astype(str) == str(project_id)]
    if metric_number is not None:
        result = result[
            pd.to_numeric(result["MetricNumber"], errors="coerce")
            == int(metric_number)
        ]
    selected_statuses = set(statuses)
    if selected_statuses:
        result = result[result["Status"].isin(selected_statuses)]
    return result.sort_values(
        ["ProjectName", "ProjectID", "MetricNumber"],
        kind="stable",
    ).reset_index(drop=True)


def supporting_conditions(
    conditions: pd.DataFrame,
    assessment_scope: pd.DataFrame,
) -> pd.DataFrame:
    """Return saved condition rows supporting the visible assessment scope."""

    if conditions.empty or assessment_scope.empty:
        return conditions.iloc[0:0].copy()
    keys = assessment_scope[["ProjectID", "RuleID"]].drop_duplicates().copy()
    keys["ProjectID"] = keys["ProjectID"].astype(str)
    prepared = conditions.copy()
    prepared["ProjectID"] = prepared["ProjectID"].astype(str)
    return (
        prepared.merge(keys, on=["ProjectID", "RuleID"], how="inner")
        .sort_values(
            ["MetricNumber", "ProjectName", "EntityType", "EntityID"],
            kind="stable",
        )
        .reset_index(drop=True)
    )


def status_label(value: Any) -> str:
    """Translate a recorded status code without changing its semantics."""

    text = "" if pd.isna(value) else str(value)
    return STATUS_LABELS.get(text, text.replace("_", " ").title())


def status_date_source_label(value: Any) -> str:
    """Translate recorded status-date provenance for display."""

    text = "" if pd.isna(value) else str(value)
    return STATUS_DATE_SOURCE_LABELS.get(
        text, text.replace("_", " ").title()
    )


def truthy(values: pd.Series) -> pd.Series:
    """Normalise CSV boolean values for presentation filtering."""

    return values.fillna(False).map(
        lambda value: value is True
        or str(value).strip().lower() in {"1", "true", "yes", "y"}
    )


def unavailable_measures(metrics: dict[str, Any]) -> pd.DataFrame:
    """Flatten backend-recorded unavailable measures for display."""

    rows = []
    for item in metrics.get("unavailable_measures", []):
        if isinstance(item, dict):
            reasons = item.get("reasons", [])
            rows.append({
                "Metric": item.get("metric_name", "Unavailable metric"),
                "Rule ID": item.get("rule_id", ""),
                "Reason": "; ".join(str(reason) for reason in reasons),
            })
        else:
            rows.append({
                "Metric": str(item).replace("_", " ").title(),
                "Rule ID": "",
                "Reason": "Not recorded",
            })
    return pd.DataFrame(rows, columns=["Metric", "Rule ID", "Reason"])
