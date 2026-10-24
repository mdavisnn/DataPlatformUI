"""Factual presentation and editable assumptions for saved scenario runs."""

from __future__ import annotations

from copy import deepcopy
import json
from typing import Any

import pandas as pd

from services.scenario_planning import default_project_policies


OBJECTIVE_LABELS = {
    "protect_priority": "Protect high-priority projects",
    "minimise_total_slippage": "Reduce total slippage",
    "minimise_changes": "Make fewer changes",
}
OBJECTIVE_HELP = {
    "protect_priority": "Rank options using the engine's project-priority objective.",
    "minimise_total_slippage": "Rank options using the engine's total-slippage objective.",
    "minimise_changes": "Rank options using the engine's change-minimisation objective.",
}


def option_label(index: int) -> str:
    return f"Option {chr(65 + index)}"


def planning_signature(planning: dict[str, Any]) -> str:
    """Compare planning values independently of list ordering and date types."""
    normalised = deepcopy(planning)
    for key in ("allowed_actions", "projects", "resource_substitutions", "targets"):
        normalised[key] = sorted(
            normalised.get(key, []),
            key=lambda value: json.dumps(value, sort_keys=True, default=str),
        )
    return json.dumps(normalised, sort_keys=True, default=str)


def draft_from_planning(
    planning: dict[str, Any], projects: pd.DataFrame,
) -> dict[str, Any]:
    """Restore all saved planning assumptions without sharing mutable values."""
    policies = default_project_policies(projects)
    saved_policies = {item["project_id"]: item for item in planning.get("projects", [])}
    for index, row in policies.iterrows():
        saved = saved_policies.get(row["ProjectID"])
        if saved:
            policies.loc[index, "Protection"] = saved["protection"]
            policies.loc[index, "Priority"] = saved["priority"]
            policies.loc[index, "Max movement (days)"] = saved[
                "max_finish_movement_calendar_days"
            ]
    return {
        "planning": deepcopy(planning),
        "policies": policies,
        "substitutions": pd.DataFrame([
            {
                "TaskID": item["task_id"],
                "FromResourceID": item["from_resource_id"],
                "ToResourceID": item["to_resource_id"],
            }
            for item in planning.get("resource_substitutions", [])
        ], columns=["TaskID", "FromResourceID", "ToResourceID"]).astype("string"),
        "targets": pd.DataFrame([
            {
                "TargetID": item["target_id"],
                "Type": item["type"],
                "EntityID": item["entity_id"],
                "TargetDate": (
                    pd.Timestamp(item["target_date"]).date()
                    if pd.notna(item.get("target_date")) else None
                ),
                "Treatment": item["treatment"],
            }
            for item in planning.get("targets", [])
        ], columns=["TargetID", "Type", "EntityID", "TargetDate", "Treatment"]),
    }


def planning_from_editors(
    values: dict[str, Any], policies: pd.DataFrame,
    substitutions: pd.DataFrame, targets: pd.DataFrame,
) -> dict[str, Any]:
    """Snapshot draft inputs for comparison; the execution adapter validates them."""
    planning = deepcopy(values)
    planning["projects"] = [
        {
            "project_id": row["ProjectID"],
            "protection": row["Protection"],
            "priority": row["Priority"],
            "max_finish_movement_calendar_days": row["Max movement (days)"],
        }
        for row in policies.to_dict("records")
    ]
    planning["resource_substitutions"] = [
        {
            "task_id": row["TaskID"], "from_resource_id": row["FromResourceID"],
            "to_resource_id": row["ToResourceID"],
        }
        for row in substitutions.dropna(how="all").to_dict("records")
    ]
    planning["targets"] = [
        {
            "target_id": row["TargetID"], "type": row["Type"],
            "entity_id": row["EntityID"],
            "target_date": str(row["TargetDate"]) if pd.notna(row["TargetDate"]) else None,
            "treatment": row["Treatment"],
        }
        for row in targets.dropna(how="all").to_dict("records")
    ]
    return planning


def finish_movement_frame(
    generation: dict[str, Any], candidate: dict[str, Any],
    planning: dict[str, Any],
) -> pd.DataFrame:
    """Include unchanged and protected projects; missing dates stay unknown."""
    baseline = (generation.get("baseline", {}).get("schedule") or {}).get("projects", [])
    result = candidate.get("result", {})
    scenario = (result.get("schedule") or {}).get("projects", [])
    by_id = {item["project_id"]: item for item in scenario}
    movements = {item["project_id"]: item for item in result.get("project_movements", [])}
    policies = {item["project_id"]: item for item in planning.get("projects", [])}
    rows = []
    for project in baseline:
        identifier = project["project_id"]
        movement = movements.get(identifier, {})
        alternative = by_id.get(identifier, {})
        before = pd.to_datetime(
            project.get("scheduled_finish_date", movement.get("source_finish_date")),
            errors="coerce",
        )
        after = pd.to_datetime(
            alternative.get("scheduled_finish_date", movement.get("scenario_finish_date")),
            errors="coerce",
        )
        rows.append({
            "Project ID": identifier,
            "Project": project.get("project_name") or identifier,
            "Baseline finish": before,
            "Scenario finish": after,
            "Movement (days)": int((after - before).days)
            if pd.notna(before) and pd.notna(after) else None,
            "Protection": policies.get(identifier, {}).get("protection", "Not recorded"),
        })
    return pd.DataFrame(rows, columns=[
        "Project ID", "Project", "Baseline finish", "Scenario finish",
        "Movement (days)", "Protection",
    ])


def overloaded_resource_days(records: list[dict] | None) -> int | None:
    """Sum inclusive overload days per resource, merging overlapping intervals."""
    if records is None:
        return None
    intervals: dict[str, list[tuple[pd.Timestamp, pd.Timestamp]]] = {}
    for item in records:
        if not item.get("over_capacity"):
            continue
        start = pd.to_datetime(item.get("start_date"), errors="coerce")
        finish = pd.to_datetime(item.get("finish_date"), errors="coerce")
        if pd.isna(start) or pd.isna(finish) or finish < start:
            return None
        intervals.setdefault(item["resource_id"], []).append((start, finish))
    total = 0
    for periods in intervals.values():
        end = None
        for start, finish in sorted(periods):
            if end is not None:
                start = max(start, end + pd.Timedelta(1, unit="D"))
            if finish >= start:
                total += (finish - start).days + 1
            end = max(end, finish) if end is not None else finish
    return total


def option_story(
    generation: dict[str, Any], candidate: dict[str, Any],
    planning: dict[str, Any],
    task_names: dict[str, str] | None = None,
    resource_names: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Explain measured benefits and costs without inferring cause or optimality."""
    result = candidate.get("result", {})
    proposal = candidate.get("proposal", {})
    before = overloaded_resource_days(generation.get("baseline", {}).get("resource_load"))
    after = overloaded_resource_days(result.get("resource_load"))
    finishes = finish_movement_frame(generation, candidate, planning)
    known = finishes.dropna(subset=["Movement (days)"])
    delayed = known.loc[known["Movement (days)"] > 0]
    earlier = known.loc[known["Movement (days)"] < 0]
    direct_moves = proposal.get("task_date_changes", [])
    reassignments = proposal.get("resource_reassignments", [])
    changed_task_ids = {
        item["entity_id"] for item in result.get("date_deltas", [])
        if item.get("entity_type") == "task" and item.get("origin") != "unchanged"
    } | {item["task_id"] for item in [*direct_moves, *reassignments]}
    if before is None or after is None:
        benefit = "Comparable resource-pressure evidence is unavailable."
    elif after < before:
        benefit = f"Overloaded resource-days fall from {before} to {after}."
    elif after > before:
        benefit = f"Overloaded resource-days rise from {before} to {after}."
    else:
        benefit = f"Overloaded resource-days remain at {after}."
    if not earlier.empty:
        benefit += f" {len(earlier)} project(s) finish earlier."
    changes = (
        f"{len(direct_moves)} direct task move(s), {len(reassignments)} "
        f"resource reassignment(s); {len(changed_task_ids)} task(s) affected."
    )
    task_names = task_names or {}
    resource_names = resource_names or {}
    actions = [
        f"Move {task_names.get(item['task_id'], item['task_id'])} to "
        f"{item.get('proposed_start_date', 'the recorded start')}–"
        f"{item.get('proposed_finish_date', 'the recorded finish')}."
        for item in direct_moves
    ] + [
        f"Reassign {task_names.get(item['task_id'], item['task_id'])} from "
        f"{resource_names.get(item['from_resource_id'], item['from_resource_id'])} to "
        f"{resource_names.get(item['to_resource_id'], item['to_resource_id'])}."
        for item in reassignments
    ]
    if not delayed.empty:
        names = ", ".join(delayed["Project"].astype(str).head(3))
        trade_off = (
            f"{len(delayed)} project(s) finish later: {names}. "
            f"Largest delay: {int(delayed['Movement (days)'].max())} calendar days."
        )
    elif len(known) == len(finishes) and not finishes.empty:
        trade_off = "No project finishes later than the baseline."
    else:
        trade_off = "Project finish-date trade-offs are not fully recorded."
    missed = [item for item in candidate.get("target_outcomes", []) if item.get("status") == "missed"]
    if missed:
        trade_off += f" {len(missed)} configured target(s) missed."
    protected = finishes.loc[finishes["Protection"] == "protected"]
    if not protected.empty:
        if protected["Movement (days)"].isna().any():
            protection = "Some protected-project finish dates are unavailable."
        elif protected["Movement (days)"].eq(0).all():
            protection = f"All {len(protected)} protected project finish dates are unchanged."
        else:
            protection = "Review recorded movement on protected projects."
    else:
        protection = "No projects were configured as protected."
    return {
        "benefit": benefit, "changes": changes, "trade_off": trade_off,
        "protection": protection, "baseline_overload_days": before,
        "scenario_overload_days": after,
        "delayed_projects": len(delayed) if len(known) == len(finishes) and len(finishes) else None,
        "tasks_changed": len(changed_task_ids), "actions": actions,
    }


def generation_guidance(generation: dict[str, Any]) -> tuple[str, str]:
    status = generation.get("status")
    if status == "input_not_fit":
        return (
            "Baseline needs attention",
            "Review the blocking input-fitness conditions in Assumptions and run evidence. "
            "Correct the source evidence and assess a new observation before trying again.",
        )
    if status == "no_change_needed":
        return (
            "No change needed under these assumptions",
            "The unchanged schedule passed the configured checks. Review the baseline "
            "and targets before changing your assumptions.",
        )
    if generation.get("search_truncated") or status == "search_truncated":
        return (
            "Search limit reached",
            "The bounded search stopped at a configured limit. Any options shown are "
            "the highest-ranked feasible options found so far. You can deliberately "
            "increase candidate limit or action depth in Advanced settings.",
        )
    if not generation.get("selected_candidates"):
        return (
            "No feasible option found",
            "The candidates explored did not satisfy all configured constraints. "
            "Review the recorded blockers, then consider the horizon, movement limits "
            "or explicitly permitted substitutions. This does not prove that no solution exists.",
        )
    return (
        "Options ready to discuss",
        "Options follow the saved ranking objective. Compare their benefits and "
        "trade-offs; the bounded search does not establish a global optimum.",
    )
