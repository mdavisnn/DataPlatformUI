"""Seed synthetic governed products so the console can be reviewed safely."""

from __future__ import annotations

import json
from pathlib import Path

from config.settings import Settings


CLIENT_ID = "demo-ui"
SNAPSHOT_ID = "demo-2026-08-31"


def _write_text(root: Path, key: str, content: str) -> None:
    root = root.resolve()
    path = (root / key).resolve()
    if root not in path.parents:
        raise ValueError(f"Demo object escapes governed storage: {key}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="")


def _write_json(root: Path, key: str, value: dict) -> None:
    _write_text(root, key, json.dumps(value, indent=2, sort_keys=True))


def main(settings: Settings | None = None) -> int:
    settings = settings or Settings.from_environment()
    metadata = settings.storage_root / "metadata"
    curated = settings.storage_root / "curated"
    run_id = "demo-run-001"
    _write_json(metadata, f"runs/{run_id}/run_summary.json", {
        "client_id": CLIENT_ID,
        "run_id": run_id,
        "status": "assessed",
        "profile_status": "success",
        "fitness_status": "fit_with_caveats",
        "observation_date": "2026-08-31",
        "snapshot_id": SNAPSHOT_ID,
        "source_files": [
            "projects_demo.csv",
            "tasks_demo.csv",
            "resources_demo.csv",
            "assignments_demo.csv",
        ],
        "datasets_discovered": ["projects", "tasks", "resources", "assignments"],
        "notes": ["Synthetic demonstration evidence."],
    })
    _write_json(metadata, f"snapshots/{SNAPSHOT_ID}/snapshot.json", {
        "client_id": CLIENT_ID,
        "snapshot_id": SNAPSHOT_ID,
        "run_id": run_id,
        "observation_date": "2026-08-31",
        "history_eligible": True,
        "datasets": {
            "projects": "snapshots/demo/projects.csv",
            "tasks": "snapshots/demo/tasks.csv",
            "resources": "snapshots/demo/resources.csv",
            "assignments": "snapshots/demo/assignments.csv",
        },
        "source_files": [
            "projects_demo.csv",
            "tasks_demo.csv",
            "resources_demo.csv",
            "assignments_demo.csv",
        ],
    })
    capabilities = {
        "data": {"status": "fit", "blocking_conditions": [], "caveats": [], "unavailable_rules": []},
        "schedule": {
            "status": "fit_with_caveats",
            "blocking_conditions": [],
            "caveats": [{"rule_id": "FIT-DATE-003", "dataset": "tasks", "count": 9}],
            "unavailable_rules": [],
        },
        "resource": {"status": "fit", "blocking_conditions": [], "caveats": [], "unavailable_rules": []},
        "portfolio": {"status": "fit", "blocking_conditions": [], "caveats": [], "unavailable_rules": []},
        "reporting": {"status": "fit", "blocking_conditions": [], "caveats": [], "unavailable_rules": []},
        "history": {
            "status": "fit_with_caveats",
            "blocking_conditions": [],
            "caveats": [{"rule_id": "FIT-HIST-001", "dataset": "projects", "count": 1}],
            "unavailable_rules": [],
        },
    }
    _write_json(metadata, f"snapshots/{SNAPSHOT_ID}/fitness.json", {
        "client_id": CLIENT_ID,
        "snapshot_id": SNAPSHOT_ID,
        "capabilities": capabilities,
    })
    findings = [
        {
            "finding_id": "SCH-001",
            "diagnostic_id": "schedule_health",
            "domain": "schedule",
            "title": "Activities extend beyond project forecasts",
            "description": "Fourteen active projects contain activities finishing after the project forecast finish date.",
            "snapshot_id": SNAPSHOT_ID,
            "observation_date": "2026-08-31",
            "rule_id": "SCH-OUTSIDE-PROJECT-DATES",
            "severity": "high",
            "evidence": {"projects_affected": 14, "activities_affected": 67, "portfolio_projects": 42},
            "affected_entities": {"projects": [f"PRJ-{number:03}" for number in range(1, 15)]},
            "supporting_artifacts": [f"curated/snapshots/{SNAPSHOT_ID}/schedule/tasks_outside_project_dates.csv"],
        },
        {
            "finding_id": "RES-001",
            "diagnostic_id": "resource_conflicts",
            "domain": "resource",
            "title": "Persistent allocation conflicts",
            "description": "Seven resources are allocated above available capacity across overlapping assignments.",
            "snapshot_id": SNAPSHOT_ID,
            "observation_date": "2026-08-31",
            "rule_id": "RES-OVERALLOCATED",
            "severity": "medium",
            "evidence": {"resources_affected": 7, "maximum_allocation_percent": 165},
            "affected_entities": {"resources": [f"RES-{number:03}" for number in range(1, 8)]},
            "supporting_artifacts": [f"curated/snapshots/{SNAPSHOT_ID}/resource/resource_conflicts.csv"],
        },
        {
            "finding_id": "PORT-001",
            "diagnostic_id": "portfolio_health",
            "domain": "portfolio",
            "title": "Forecast exposure is concentrated",
            "description": "Five projects account for most of the portfolio's observed forecast delay.",
            "snapshot_id": SNAPSHOT_ID,
            "observation_date": "2026-08-31",
            "rule_id": "PORT-DELAY-CONCENTRATION",
            "severity": "medium",
            "evidence": {"projects_affected": 5, "share_of_total_delay_percent": 71},
            "affected_entities": {"projects": [f"PRJ-{number:03}" for number in range(1, 6)]},
            "supporting_artifacts": [],
        },
    ]
    _write_json(metadata, f"snapshots/{SNAPSHOT_ID}/findings.json", {
        "client_id": CLIENT_ID,
        "snapshot_id": SNAPSHOT_ID,
        "observation_date": "2026-08-31",
        "findings": findings,
    })
    _write_json(metadata, f"snapshots/{SNAPSHOT_ID}/diagnosis.json", {
        "client_id": CLIENT_ID,
        "snapshot_id": SNAPSHOT_ID,
        "stage": "diagnosis",
        "execution_status": "completed_with_limitations",
        "observation_date": "2026-08-31",
        "capability_fitness": capabilities,
        "diagnostics": [{"capability": "schedule", "status": "success", "finding_count": 1}],
    })
    _write_text(
        curated,
        f"snapshots/{SNAPSHOT_ID}/schedule/tasks_outside_project_dates.csv",
        "ProjectID,TaskID,ProjectForecastFinish,TaskFinish,DaysOutside\nPRJ-001,TASK-001,2026-10-01,2026-11-15,45\nPRJ-004,TASK-019,2026-09-12,2026-10-03,21\n",
    )
    _write_text(
        curated,
        f"snapshots/{SNAPSHOT_ID}/resource/resource_conflicts.csv",
        "ResourceID,Period,AllocationPercent,ExcessPercent\nRES-001,2026-09,165,65\nRES-003,2026-09,135,35\n",
    )
    print(f"Synthetic console demo created for {CLIENT_ID}: {SNAPSHOT_ID}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
