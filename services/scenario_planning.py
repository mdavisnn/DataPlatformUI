"""SchedulePlatform execution and persisted-result adapters."""

from __future__ import annotations

from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any, Iterable
from uuid import uuid4

import pandas as pd

from config.settings import Settings
from services.catalog import validate_client_id


_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_OBJECTIVES = {
    "protect_priority",
    "minimise_total_slippage",
    "minimise_changes",
}
_ACTIONS = {"move_task_dates", "reassign_resource"}
_PROTECTIONS = {"protected", "flexible"}
_TARGET_TYPES = {"project_finish", "task_finish"}
_TARGET_TREATMENTS = {"report_only", "hard_constraint"}


class ScenarioPlanningError(RuntimeError):
    """Raised when scenario configuration or execution cannot be completed."""


def schedule_platform_ready(settings: Settings) -> tuple[bool, str]:
    path = settings.schedule_platform_path
    expected = path / "src" / "schedule_platform" / "cli.py"
    if not path.is_dir() or not expected.is_file():
        return False, (
            "SchedulePlatform is not available at "
            f"{path}. Configure SCHEDULE_PLATFORM_PATH."
        )
    schema_directory = settings.platform_path / "schemas"
    if not schema_directory.is_dir():
        return False, f"DataPlatform schema directory is unavailable: {schema_directory}"
    return True, str(path)


def default_project_policies(projects: pd.DataFrame) -> pd.DataFrame:
    required = {"ProjectID", "ProjectName"}
    if not required.issubset(projects.columns):
        missing = sorted(required - set(projects.columns))
        raise ScenarioPlanningError(
            f"Canonical projects are missing required fields: {missing}"
        )
    policies = (
        projects[["ProjectID", "ProjectName"]]
        .dropna(subset=["ProjectID"])
        .drop_duplicates(subset=["ProjectID"])
        .copy()
    )
    policies["ProjectID"] = policies["ProjectID"].astype(str)
    policies["ProjectName"] = policies["ProjectName"].fillna(
        policies["ProjectID"]
    ).astype(str)
    policies["Protection"] = "flexible"
    policies["Priority"] = 2
    policies["Max movement (days)"] = 30
    return policies.sort_values(["ProjectName", "ProjectID"]).reset_index(
        drop=True
    )


def empty_substitutions() -> pd.DataFrame:
    return pd.DataFrame({
        "TaskID": pd.Series(dtype="string"),
        "FromResourceID": pd.Series(dtype="string"),
        "ToResourceID": pd.Series(dtype="string"),
    })


def empty_targets() -> pd.DataFrame:
    return pd.DataFrame({
        "TargetID": pd.Series(dtype="string"),
        "Type": pd.Series(dtype="string"),
        "EntityID": pd.Series(dtype="string"),
        "TargetDate": pd.Series(dtype="object"),
        "Treatment": pd.Series(dtype="string"),
    })


def _text(value: Any, field: str) -> str:
    if value is None or pd.isna(value) or not str(value).strip():
        raise ScenarioPlanningError(f"{field} must be supplied")
    return str(value).strip()


def _whole_number(value: Any, field: str, *, minimum: int) -> int:
    try:
        numeric = float(value)
    except (TypeError, ValueError) as error:
        raise ScenarioPlanningError(f"{field} must be a whole number") from error
    if not numeric.is_integer() or numeric < minimum:
        raise ScenarioPlanningError(
            f"{field} must be a whole number of at least {minimum}"
        )
    return int(numeric)


def _nonblank_records(frame: pd.DataFrame | None) -> list[dict[str, Any]]:
    if frame is None or frame.empty:
        return []
    records = []
    for record in frame.to_dict("records"):
        if any(not pd.isna(value) and str(value).strip() for value in record.values()):
            records.append(record)
    return records


def _iso_date(value: Any, field: str) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = _text(value, field)
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError as error:
        raise ScenarioPlanningError(
            f"{field} must be an ISO date"
        ) from error


def build_configuration_document(
    settings: Settings,
    *,
    client_id: str,
    snapshot_id: str,
    objective: str,
    scenario_count: int,
    candidate_limit: int,
    max_action_depth: int,
    allowed_actions: Iterable[str],
    allow_assignment_date_fallback: bool,
    project_policies: pd.DataFrame,
    resource_substitutions: pd.DataFrame | None = None,
    targets: pd.DataFrame | None = None,
) -> dict[str, Any]:
    client_id = validate_client_id(client_id)
    if not _SAFE_IDENTIFIER.fullmatch(str(snapshot_id or "")):
        raise ScenarioPlanningError("snapshot_id is not a safe identifier")
    if objective not in _OBJECTIVES:
        raise ScenarioPlanningError("Unsupported planning objective")
    scenario_count = _whole_number(
        scenario_count, "Scenario count", minimum=1
    )
    candidate_limit = _whole_number(
        candidate_limit, "Candidate limit", minimum=1
    )
    max_action_depth = _whole_number(
        max_action_depth, "Maximum action depth", minimum=1
    )
    if scenario_count > candidate_limit:
        raise ScenarioPlanningError(
            "Scenario count must not exceed the candidate limit"
        )
    actions = list(dict.fromkeys(str(item) for item in allowed_actions))
    if not actions or any(item not in _ACTIONS for item in actions):
        raise ScenarioPlanningError("Select at least one supported action")

    project_records = []
    seen_projects: set[str] = set()
    for index, row in enumerate(_nonblank_records(project_policies), start=1):
        project_id = _text(row.get("ProjectID"), f"Project row {index} ID")
        if project_id in seen_projects:
            raise ScenarioPlanningError(
                f"Project policy repeats {project_id!r}"
            )
        seen_projects.add(project_id)
        protection = _text(
            row.get("Protection"), f"Project {project_id} protection"
        ).lower()
        if protection not in _PROTECTIONS:
            raise ScenarioPlanningError(
                f"Project {project_id} has an unsupported protection status"
            )
        project_records.append({
            "project_id": project_id,
            "protection": protection,
            "priority": _whole_number(
                row.get("Priority"),
                f"Project {project_id} priority",
                minimum=1,
            ),
            "max_finish_movement_calendar_days": _whole_number(
                row.get("Max movement (days)"),
                f"Project {project_id} movement limit",
                minimum=0,
            ),
        })
        if project_records[-1]["priority"] > 3:
            raise ScenarioPlanningError(
                f"Project {project_id} priority must be 1, 2 or 3"
            )
    if not project_records:
        raise ScenarioPlanningError("At least one project policy is required")

    substitutions = []
    for index, row in enumerate(
        _nonblank_records(resource_substitutions), start=1
    ):
        substitutions.append({
            "task_id": _text(row.get("TaskID"), f"Substitution row {index} task"),
            "from_resource_id": _text(
                row.get("FromResourceID"),
                f"Substitution row {index} source resource",
            ),
            "to_resource_id": _text(
                row.get("ToResourceID"),
                f"Substitution row {index} replacement resource",
            ),
        })
    if substitutions and "reassign_resource" not in actions:
        raise ScenarioPlanningError(
            "Resource substitutions require the reassign resource action"
        )

    configured_targets = []
    for index, row in enumerate(_nonblank_records(targets), start=1):
        target_type = _text(
            row.get("Type"), f"Target row {index} type"
        ).lower()
        treatment = _text(
            row.get("Treatment"), f"Target row {index} treatment"
        ).lower()
        if target_type not in _TARGET_TYPES:
            raise ScenarioPlanningError(
                f"Target row {index} has an unsupported type"
            )
        if treatment not in _TARGET_TREATMENTS:
            raise ScenarioPlanningError(
                f"Target row {index} has an unsupported treatment"
            )
        configured_targets.append({
            "target_id": _text(
                row.get("TargetID"), f"Target row {index} ID"
            ),
            "type": target_type,
            "entity_id": _text(
                row.get("EntityID"), f"Target row {index} entity"
            ),
            "target_date": _iso_date(
                row.get("TargetDate"), f"Target row {index} date"
            ),
            "treatment": treatment,
        })

    return {
        "config_version": "1.0",
        "input": {
            "type": "processed",
            "root": str(settings.storage_root),
            "schema_directory": str(settings.platform_path / "schemas"),
            "client_id": client_id,
            "snapshot_id": snapshot_id,
        },
        "planning": {
            "objective": objective,
            "scenario_count": scenario_count,
            "candidate_limit": candidate_limit,
            "max_action_depth": max_action_depth,
            "allowed_actions": actions,
            "allow_assignment_date_fallback": bool(
                allow_assignment_date_fallback
            ),
            "projects": project_records,
            "resource_substitutions": substitutions,
            "targets": configured_targets,
        },
        "risk": {
            "enabled": False,
            "iterations": None,
            "seed": None,
            "task_durations": [],
            "targets": [],
        },
        "output": {"root": str(settings.schedule_output_root)},
    }


def _new_run_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"ui-{timestamp}-{uuid4().hex[:8]}"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ScenarioPlanningError(
            f"SchedulePlatform artifact is unreadable: {path}"
        ) from error
    if not isinstance(document, dict):
        raise ScenarioPlanningError(
            f"SchedulePlatform artifact is not a JSON object: {path}"
        )
    return document


def load_generation_package(
    settings: Settings,
    run_root: str | Path,
) -> dict[str, Any]:
    output_root = settings.schedule_output_root.resolve()
    root = Path(run_root).resolve()
    if root == output_root or not root.is_relative_to(output_root):
        raise ScenarioPlanningError(
            "Scenario run resolves outside the configured output root"
        )
    run = _read_json(root / "run.json")
    artifacts = run.get("artifacts", {})
    generation_name = artifacts.get("generation_result")
    configuration_name = artifacts.get("configuration")
    if (
        not isinstance(generation_name, str)
        or Path(generation_name).name != generation_name
        or not isinstance(configuration_name, str)
        or Path(configuration_name).name != configuration_name
    ):
        raise ScenarioPlanningError("Scenario run has unsafe artifact references")
    return {
        "root": root,
        "run": run,
        "configuration": _read_json(root / configuration_name),
        "generation": _read_json(root / generation_name),
    }


def list_generation_packages(
    settings: Settings,
    client_id: str,
    snapshot_id: str,
) -> list[dict[str, Any]]:
    owner = validate_client_id(client_id)
    runs_root = settings.schedule_output_root / owner / "runs"
    if not runs_root.is_dir():
        return []
    packages = []
    for root in runs_root.iterdir():
        if not root.is_dir() or not _SAFE_IDENTIFIER.fullmatch(root.name):
            continue
        try:
            package = load_generation_package(settings, root)
        except ScenarioPlanningError:
            continue
        run = package["run"]
        if (
            run.get("client_id") == owner
            and run.get("snapshot_id") == snapshot_id
        ):
            packages.append(package)
    return sorted(
        packages,
        key=lambda item: (
            str(item["run"].get("completed_at") or ""),
            str(item["run"].get("run_id") or ""),
        ),
        reverse=True,
    )


def run_scenario_generation(
    settings: Settings,
    configuration: dict[str, Any],
    *,
    run_id: str | None = None,
) -> dict[str, Any]:
    ready, message = schedule_platform_ready(settings)
    if not ready:
        raise ScenarioPlanningError(message)
    active_run_id = run_id or _new_run_id()
    if not _SAFE_IDENTIFIER.fullmatch(active_run_id):
        raise ScenarioPlanningError("run_id is not a safe identifier")

    environment = os.environ.copy()
    source_root = settings.schedule_platform_path / "src"
    existing_pythonpath = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = os.pathsep.join(
        value
        for value in (str(source_root), existing_pythonpath)
        if value
    )
    with tempfile.TemporaryDirectory(prefix="schedule-platform-ui-") as temporary:
        config_path = Path(temporary) / "analysis-config.json"
        config_path.write_text(
            json.dumps(
                configuration,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        command = [
            sys.executable,
            "-m",
            "schedule_platform.cli",
            "generate",
            "--config",
            str(config_path),
            "--run-id",
            active_run_id,
        ]
        try:
            completed = subprocess.run(
                command,
                cwd=settings.schedule_platform_path,
                env=environment,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=900,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ScenarioPlanningError(
                f"Could not run SchedulePlatform: {error}"
            ) from error
    output = "\n".join(
        part for part in (completed.stdout, completed.stderr) if part
    ).strip()
    if completed.returncode != 0:
        raise ScenarioPlanningError(
            output or "SchedulePlatform generation failed without output"
        )
    try:
        package_reference = json.loads(
            next(
                line for line in reversed(completed.stdout.splitlines())
                if line.strip()
            )
        )
        run_root = package_reference["root"]
    except (StopIteration, KeyError, TypeError, json.JSONDecodeError) as error:
        raise ScenarioPlanningError(
            "SchedulePlatform did not return a valid package reference"
        ) from error
    package = load_generation_package(settings, run_root)
    package["command_output"] = output
    return package


def candidate_summary_frame(generation: dict[str, Any]) -> pd.DataFrame:
    baseline_overloads = sum(
        bool(item.get("over_capacity"))
        for item in generation.get("baseline", {}).get("resource_load", [])
    )
    rows = []
    for rank, candidate in enumerate(
        generation.get("selected_candidates", []), start=1
    ):
        result = candidate.get("result", {})
        proposal = candidate.get("proposal", {})
        task_moves = proposal.get("task_date_changes", [])
        reassignments = proposal.get("resource_reassignments", [])
        metrics = {
            item.get("name"): item.get("value")
            for item in result.get("objective_metrics", [])
        }
        scenario_overloads = sum(
            bool(item.get("over_capacity"))
            for item in result.get("resource_load", [])
        )
        movements = [
            abs(int(item.get("movement_calendar_days") or 0))
            for item in result.get("project_movements", [])
        ]
        rows.append({
            "Rank": rank,
            "ProposalID": proposal.get("proposal_id"),
            "Feasibility": result.get("feasibility_status"),
            "Primary action": _primary_action_label(
                task_moves, reassignments
            ),
            "Over-capacity intervals": (
                f"{baseline_overloads} → {scenario_overloads}"
            ),
            "Maximum finish movement (days)": max(movements, default=0),
            "Action depth": candidate.get("action_depth"),
            "Task moves": len(task_moves),
            "Reassignments": len(reassignments),
            **metrics,
        })
    return pd.DataFrame(rows)


def _primary_action_label(
    task_moves: list[dict[str, Any]],
    reassignments: list[dict[str, Any]],
) -> str:
    if len(task_moves) == 1 and not reassignments:
        return f"Move {task_moves[0].get('task_id', 'task')}"
    if len(reassignments) == 1 and not task_moves:
        return f"Reassign {reassignments[0].get('task_id', 'task')}"
    parts = []
    if task_moves:
        parts.append(f"{len(task_moves)} task move(s)")
    if reassignments:
        parts.append(f"{len(reassignments)} reassignment(s)")
    return " + ".join(parts) or "No direct action"


def assignment_change_frame(candidate: dict[str, Any]) -> pd.DataFrame:
    """Return assignments whose resource or scheduled dates changed."""

    assignments = (
        candidate.get("result", {}).get("schedule") or {}
    ).get("assignments", [])
    rows = []
    for item in assignments:
        resource_changed = (
            item.get("source_resource_id")
            != item.get("scheduled_resource_id")
        )
        dates_changed = (
            item.get("source_start_date")
            != item.get("scheduled_start_date")
            or item.get("source_finish_date")
            != item.get("scheduled_finish_date")
        )
        if not resource_changed and not dates_changed:
            continue
        change = (
            "Resource and dates"
            if resource_changed and dates_changed
            else "Resource" if resource_changed else "Dates"
        )
        rows.append({
            "Task": item.get("task_id"),
            "Change": change,
            "Baseline resource": item.get("source_resource_id"),
            "Scenario resource": item.get("scheduled_resource_id"),
            "Allocation (%)": item.get("allocation"),
            "Baseline start": pd.to_datetime(
                item.get("source_start_date"), errors="coerce"
            ),
            "Baseline finish": pd.to_datetime(
                item.get("source_finish_date"), errors="coerce"
            ),
            "Scenario start": pd.to_datetime(
                item.get("scheduled_start_date"), errors="coerce"
            ),
            "Scenario finish": pd.to_datetime(
                item.get("scheduled_finish_date"), errors="coerce"
            ),
        })
    return pd.DataFrame(rows)


def _resource_load_records(
    items: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    records = []
    for item in items:
        start = pd.to_datetime(item.get("start_date"), errors="coerce")
        finish = pd.to_datetime(item.get("finish_date"), errors="coerce")
        resource_id = str(item.get("resource_id") or "").strip()
        if not resource_id or pd.isna(start) or pd.isna(finish):
            continue
        records.append({
            "ResourceID": resource_id,
            "Start": start.normalize(),
            "Finish": finish.normalize(),
            "Allocation": float(item.get("total_allocation") or 0),
            "Capacity": float(item.get("capacity") or 0),
            "Over capacity": bool(item.get("over_capacity")),
        })
    return records


def _resource_signature(
    records: list[dict[str, Any]], resource_id: str
) -> tuple[tuple[Any, ...], ...]:
    return tuple(sorted(
        (
            item["Start"],
            item["Finish"],
            item["Allocation"],
            item["Capacity"],
            item["Over capacity"],
        )
        for item in records
        if item["ResourceID"] == resource_id
    ))


def affected_resource_ids(
    generation: dict[str, Any], candidate: dict[str, Any]
) -> list[str]:
    """Identify resources whose load or assignment differs from baseline."""

    baseline = _resource_load_records(
        generation.get("baseline", {}).get("resource_load", [])
    )
    scenario = _resource_load_records(
        candidate.get("result", {}).get("resource_load", [])
    )
    resource_ids = {
        item["ResourceID"] for item in [*baseline, *scenario]
    }
    affected = {
        resource_id
        for resource_id in resource_ids
        if _resource_signature(baseline, resource_id)
        != _resource_signature(scenario, resource_id)
    }
    for change in candidate.get("proposal", {}).get(
        "resource_reassignments", []
    ):
        affected.update(
            str(value)
            for value in (
                change.get("from_resource_id"),
                change.get("to_resource_id"),
            )
            if value
        )
    return sorted(affected)


def resource_impact_summary(
    generation: dict[str, Any], candidate: dict[str, Any]
) -> dict[str, int | float]:
    """Summarise deterministic resource and schedule effects."""

    baseline = _resource_load_records(
        generation.get("baseline", {}).get("resource_load", [])
    )
    scenario = _resource_load_records(
        candidate.get("result", {}).get("resource_load", [])
    )
    affected = set(affected_resource_ids(generation, candidate))
    baseline_affected = [
        item for item in baseline if item["ResourceID"] in affected
    ]
    scenario_affected = [
        item for item in scenario if item["ResourceID"] in affected
    ]
    movements = [
        abs(int(item.get("movement_calendar_days") or 0))
        for item in candidate.get("result", {}).get(
            "project_movements", []
        )
    ]
    return {
        "affected_resources": len(affected),
        "baseline_over_capacity_intervals": sum(
            item["Over capacity"] for item in baseline
        ),
        "scenario_over_capacity_intervals": sum(
            item["Over capacity"] for item in scenario
        ),
        "baseline_peak_affected_load": max(
            (item["Allocation"] for item in baseline_affected),
            default=0,
        ),
        "scenario_peak_affected_load": max(
            (item["Allocation"] for item in scenario_affected),
            default=0,
        ),
        "changed_assignments": len(assignment_change_frame(candidate)),
        "maximum_finish_movement_days": max(movements, default=0),
    }


def resource_load_comparison_frame(
    generation: dict[str, Any], candidate: dict[str, Any]
) -> pd.DataFrame:
    """Build aligned step-series around changed resource-load periods."""

    columns = [
        "ResourceID",
        "Schedule",
        "Date",
        "Allocation",
        "Capacity",
        "Over capacity",
    ]
    baseline = _resource_load_records(
        generation.get("baseline", {}).get("resource_load", [])
    )
    scenario = _resource_load_records(
        candidate.get("result", {}).get("resource_load", [])
    )
    affected = affected_resource_ids(generation, candidate)
    if not affected:
        return pd.DataFrame(columns=columns)

    differing_records = []
    for resource_id in affected:
        baseline_signature = set(_resource_signature(baseline, resource_id))
        scenario_signature = set(_resource_signature(scenario, resource_id))
        difference = baseline_signature.symmetric_difference(
            scenario_signature
        )
        differing_records.extend(
            [
                item
                for item in [*baseline, *scenario]
                if item["ResourceID"] == resource_id
                and (
                    item["Start"],
                    item["Finish"],
                    item["Allocation"],
                    item["Capacity"],
                    item["Over capacity"],
                ) in difference
            ]
        )
    focus = differing_records or [
        item
        for item in [*baseline, *scenario]
        if item["ResourceID"] in affected
    ]
    if not focus:
        return pd.DataFrame(columns=columns)
    window_start = min(item["Start"] for item in focus) - pd.Timedelta(
        7, unit="D"
    )
    window_finish = max(item["Finish"] for item in focus) + pd.Timedelta(
        7, unit="D"
    )
    window_end = window_finish + pd.Timedelta(1, unit="D")

    rows = []
    for resource_id in affected:
        combined = [
            item
            for item in [*baseline, *scenario]
            if item["ResourceID"] == resource_id
        ]
        default_capacity = max(
            (item["Capacity"] for item in combined), default=0
        )
        boundaries = {window_start, window_end}
        for item in combined:
            if item["Finish"] < window_start or item["Start"] > window_finish:
                continue
            boundaries.add(max(item["Start"], window_start))
            boundaries.add(
                min(item["Finish"] + pd.Timedelta(1, unit="D"), window_end)
            )
        for schedule, records in (
            ("Baseline", baseline),
            ("Scenario", scenario),
        ):
            matching = [
                item
                for item in records
                if item["ResourceID"] == resource_id
            ]
            for boundary in sorted(boundaries):
                active = next(
                    (
                        item
                        for item in matching
                        if item["Start"] <= boundary <= item["Finish"]
                    ),
                    None,
                )
                allocation = active["Allocation"] if active else 0
                capacity = active["Capacity"] if active else default_capacity
                rows.append({
                    "ResourceID": resource_id,
                    "Schedule": schedule,
                    "Date": boundary,
                    "Allocation": allocation,
                    "Capacity": capacity,
                    "Over capacity": allocation > capacity,
                })
    return pd.DataFrame(rows, columns=columns)


def project_comparison_frame(
    generation: dict[str, Any],
    candidate: dict[str, Any],
) -> pd.DataFrame:
    baseline = (
        generation.get("baseline", {}).get("schedule") or {}
    ).get("projects", [])
    scenario = (
        candidate.get("result", {}).get("schedule") or {}
    ).get("projects", [])
    scenario_by_id = {
        str(item.get("project_id")): item for item in scenario
    }
    rows = []
    order = 0
    for project in baseline:
        project_id = str(project.get("project_id"))
        alternative = scenario_by_id.get(project_id)
        if alternative is None:
            continue
        baseline_finish = pd.to_datetime(
            project.get("scheduled_finish_date"), errors="coerce"
        )
        scenario_finish = pd.to_datetime(
            alternative.get("scheduled_finish_date"), errors="coerce"
        )
        movement = (
            int((scenario_finish - baseline_finish).days)
            if pd.notna(baseline_finish) and pd.notna(scenario_finish)
            else None
        )
        name = str(project.get("project_name") or project_id)
        for label, source in (
            ("Baseline", project),
            ("Scenario", alternative),
        ):
            start = pd.to_datetime(
                source.get("scheduled_start_date"), errors="coerce"
            )
            finish = pd.to_datetime(
                source.get("scheduled_finish_date"), errors="coerce"
            )
            rows.append({
                "ProjectID": project_id,
                "ProjectName": name,
                "Schedule": label,
                "Start": start,
                "Finish": finish,
                "PlotFinish": finish + pd.Timedelta(1, unit="D"),
                "Lane": f"{name} · {label}",
                "LaneOrder": order,
                "Finish movement (days)": movement,
            })
            order += 1
    return pd.DataFrame(rows)
