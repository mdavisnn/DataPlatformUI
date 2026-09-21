"""Pure projections for a single-snapshot diagnostic timeline."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

import pandas as pd


SCHEDULE_COLUMNS = {
    "TaskID",
    "ProjectID",
    "TaskName",
    "ForecastStartDate",
    "ForecastFinishDate",
}


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _natural_key(value: Any) -> tuple[tuple[int, Any], ...]:
    parts = re.split(r"(\d+)", str(value or ""))
    return tuple(
        (0, int(part)) if part.isdigit() else (1, part.casefold())
        for part in parts
        if part
    )


def _entity_ids(finding: Mapping[str, Any], entity: str) -> set[str]:
    entities = finding.get("affected_entities", {})
    values = {
        str(value)
        for value in entities.get(entity, [])
        if value is not None
    }
    singular = entity.removesuffix("s")
    prefix = f"{singular}:"
    values.update(
        str(record)[len(prefix):]
        for record in entities.get("records", [])
        if str(record).startswith(prefix)
    )
    return values


def prepare_project_schedule(
    tasks: pd.DataFrame,
    project_id: str,
) -> tuple[pd.DataFrame, int]:
    """Return valid, display-ready forecast rows and the excluded row count."""

    missing = sorted(SCHEDULE_COLUMNS.difference(tasks.columns))
    if missing:
        raise ValueError(
            "Canonical tasks are missing required timeline fields: "
            + ", ".join(missing)
        )

    schedule = tasks[
        tasks["ProjectID"].astype("string") == str(project_id)
    ].copy()
    if schedule.empty:
        return schedule, 0

    for column in ("TaskID", "ProjectID", "TaskName"):
        schedule[column] = schedule[column].astype("string")
    for column in ("ForecastStartDate", "ForecastFinishDate"):
        schedule[column] = pd.to_datetime(
            schedule[column], errors="coerce"
        ).astype("datetime64[ns]")

    valid = (
        schedule["ForecastStartDate"].notna()
        & schedule["ForecastFinishDate"].notna()
        & (
            schedule["ForecastFinishDate"]
            >= schedule["ForecastStartDate"]
        )
    )
    excluded_count = int((~valid).sum())
    schedule = schedule.loc[valid].copy()
    if schedule.empty:
        return schedule, excluded_count

    if "WBS" not in schedule:
        schedule["WBS"] = ""
    if "IsMilestone" not in schedule:
        schedule["IsMilestone"] = False
    if "Status" not in schedule:
        schedule["Status"] = "Unknown"
    if "PercentComplete" not in schedule:
        schedule["PercentComplete"] = pd.NA

    schedule["IsMilestone"] = schedule["IsMilestone"].map(_truthy)
    schedule["Status"] = schedule["Status"].fillna("Unknown").astype(str)
    schedule["PlotFinish"] = schedule["ForecastFinishDate"].where(
        schedule["ForecastFinishDate"] > schedule["ForecastStartDate"],
        schedule["ForecastFinishDate"] + pd.Timedelta(1, unit="D"),
    )

    order = sorted(
        schedule.index,
        key=lambda index: (
            _natural_key(schedule.at[index, "WBS"]),
            schedule.at[index, "ForecastStartDate"],
            schedule.at[index, "TaskID"],
        ),
    )
    schedule = schedule.loc[order].reset_index(drop=True)
    schedule["Lane"] = schedule.apply(
        lambda row: (
            f"{row['WBS']} · {row['TaskName']}"
            if str(row["WBS"]).strip()
            else str(row["TaskName"])
        ),
        axis=1,
    )
    duplicate_lanes = schedule["Lane"].duplicated(keep=False)
    schedule.loc[duplicate_lanes, "Lane"] = schedule.loc[
        duplicate_lanes
    ].apply(lambda row: f"{row['Lane']} [{row['TaskID']}]", axis=1)
    schedule["LaneOrder"] = range(len(schedule))
    return schedule, excluded_count


def findings_for_project(
    findings: Iterable[Mapping[str, Any]],
    project_id: str,
    task_ids: Iterable[str],
) -> list[dict[str, Any]]:
    """Select findings explicitly linked to the project or its tasks."""

    selected_tasks = {str(value) for value in task_ids}
    selected = []
    for finding in findings:
        project_ids = _entity_ids(finding, "projects")
        finding_tasks = _entity_ids(finding, "tasks")
        if str(project_id) in project_ids or selected_tasks.intersection(
            finding_tasks
        ):
            selected.append(dict(finding))
    return selected


def _split_ids(value: Any) -> set[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return set()
    return {
        item.strip()
        for item in str(value).split(",")
        if item.strip()
    }


def _evidence_detail(row: pd.Series, finding: Mapping[str, Any]) -> str:
    message = row.get("Message")
    if pd.notna(message) and str(message).strip():
        return str(message)
    resource_name = row.get("ResourceName")
    allocation = pd.to_numeric(row.get("TotalAllocation"), errors="coerce")
    if pd.notna(resource_name) and str(resource_name).strip():
        if pd.notna(allocation):
            return f"{resource_name}: {allocation:g}% allocation"
        return str(resource_name)
    return str(finding.get("description", "Dated supporting evidence"))


def build_finding_occurrences(
    schedule: pd.DataFrame,
    findings: Iterable[Mapping[str, Any]],
    artifacts: Mapping[str, pd.DataFrame],
) -> pd.DataFrame:
    """Project dated supporting-evidence rows onto affected task lanes."""

    columns = [
        "FindingID",
        "Title",
        "RuleID",
        "Domain",
        "Severity",
        "TaskID",
        "Lane",
        "LaneOrder",
        "Start",
        "Finish",
        "PlotFinish",
        "MarkerDate",
        "OccurrenceType",
        "TimeBasis",
        "Detail",
        "Artifact",
    ]
    if schedule.empty:
        return pd.DataFrame(columns=columns)

    task_lookup = schedule.set_index("TaskID").to_dict("index")
    project_id = str(schedule.iloc[0]["ProjectID"])
    rows: list[dict[str, Any]] = []
    date_pairs = (
        ("ConflictStart", "ConflictFinish", "Conflict period"),
        ("TaskStart", "TaskFinish", "Task condition period"),
        ("StartDate", "FinishDate", "Supporting evidence period"),
    )

    for finding in findings:
        finding_id = str(finding.get("finding_id", ""))
        affected_tasks = _entity_ids(finding, "tasks")
        for reference in finding.get("supporting_artifacts", []):
            evidence = artifacts.get(str(reference))
            if evidence is None or evidence.empty:
                continue

            date_spec = next(
                (
                    (start, finish, basis)
                    for start, finish, basis in date_pairs
                    if {start, finish}.issubset(evidence.columns)
                ),
                None,
            )
            if date_spec is None:
                continue
            start_column, finish_column, time_basis = date_spec

            for _, evidence_row in evidence.iterrows():
                if "RuleID" in evidence.columns:
                    row_rule = str(evidence_row.get("RuleID", ""))
                    if row_rule and row_rule != str(finding.get("rule_id", "")):
                        continue

                row_projects = set()
                if "ProjectID" in evidence.columns:
                    row_projects.add(str(evidence_row.get("ProjectID", "")))
                if "ProjectIDs" in evidence.columns:
                    row_projects.update(_split_ids(evidence_row.get("ProjectIDs")))
                if row_projects and project_id not in row_projects:
                    continue

                row_tasks = set()
                if "TaskID" in evidence.columns:
                    row_tasks.add(str(evidence_row.get("TaskID", "")))
                if "TaskIDs" in evidence.columns:
                    row_tasks.update(_split_ids(evidence_row.get("TaskIDs")))
                row_tasks.intersection_update(task_lookup)
                if affected_tasks:
                    row_tasks.intersection_update(affected_tasks)
                if not row_tasks:
                    continue

                start = pd.to_datetime(
                    evidence_row.get(start_column), errors="coerce"
                )
                finish = pd.to_datetime(
                    evidence_row.get(finish_column), errors="coerce"
                )
                if pd.isna(start) or pd.isna(finish) or finish < start:
                    continue
                occurrence_type = "point" if start == finish else "range"
                plot_finish = (
                    finish + pd.Timedelta(1, unit="D")
                    if occurrence_type == "point"
                    else finish
                )

                for task_id in sorted(row_tasks):
                    task = task_lookup[task_id]
                    rows.append({
                        "FindingID": finding_id,
                        "Title": finding.get("title", "Untitled finding"),
                        "RuleID": finding.get("rule_id", ""),
                        "Domain": str(finding.get("domain", "unknown")).title(),
                        "Severity": str(
                            finding.get("severity", "unknown")
                        ).title(),
                        "TaskID": task_id,
                        "Lane": task["Lane"],
                        "LaneOrder": task["LaneOrder"],
                        "Start": start,
                        "Finish": finish,
                        "PlotFinish": plot_finish,
                        "MarkerDate": finish,
                        "OccurrenceType": occurrence_type,
                        "TimeBasis": time_basis,
                        "Detail": _evidence_detail(evidence_row, finding),
                        "Artifact": str(reference),
                    })

    if not rows:
        return pd.DataFrame(columns=columns)
    return (
        pd.DataFrame(rows, columns=columns)
        .drop_duplicates(
            subset=["FindingID", "TaskID", "Start", "Finish", "Detail"]
        )
        .sort_values(["LaneOrder", "Start", "FindingID"])
        .reset_index(drop=True)
    )


def selected_finding_id(event: Any) -> str | None:
    """Extract the finding identifier from a Streamlit Vega selection."""

    if not event:
        return None
    try:
        selected = event.get("selection", {}).get("finding_pick")
    except AttributeError:
        return None
    if isinstance(selected, list) and selected:
        first = selected[0]
        if isinstance(first, Mapping):
            value = first.get("FindingID")
            return str(value) if value else None
    if isinstance(selected, Mapping):
        value = selected.get("FindingID")
        return str(value) if value else None
    return None
