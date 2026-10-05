import json

import pandas as pd
import pytest

from components.scenario_charts import scenario_resource_load_chart
from config.settings import Settings
from services.scenario_planning import (
    ScenarioPlanningError,
    affected_resource_ids,
    assignment_change_frame,
    build_configuration_document,
    candidate_summary_frame,
    default_project_policies,
    list_generation_packages,
    project_comparison_frame,
    resource_impact_summary,
    resource_load_comparison_frame,
)


def _settings(tmp_path, monkeypatch):
    platform = tmp_path / "DataPlatform"
    (platform / "schemas").mkdir(parents=True)
    schedule = tmp_path / "SchedulePlatform"
    (schedule / "src" / "schedule_platform").mkdir(parents=True)
    monkeypatch.setenv("DATALAB_PLATFORM_PATH", str(platform))
    monkeypatch.setenv("SCHEDULE_PLATFORM_PATH", str(schedule))
    monkeypatch.setenv(
        "SCHEDULE_PLATFORM_OUTPUT_ROOT", str(tmp_path / "scenario-output")
    )
    monkeypatch.delenv("DATA_PLATFORM_STORAGE_ROOT", raising=False)
    return Settings.from_environment()


def _policies():
    return pd.DataFrame([
        {
            "ProjectID": "P1",
            "ProjectName": "Protected",
            "Protection": "protected",
            "Priority": 1,
            "Max movement (days)": 0,
        },
        {
            "ProjectID": "P2",
            "ProjectName": "Flexible",
            "Protection": "flexible",
            "Priority": 3,
            "Max movement (days)": 14,
        },
    ])


def test_configuration_document_keeps_risk_disabled(
    tmp_path, monkeypatch,
):
    settings = _settings(tmp_path, monkeypatch)

    document = build_configuration_document(
        settings,
        client_id="client-001",
        snapshot_id="snapshot-001",
        objective="protect_priority",
        scenario_count=2,
        candidate_limit=50,
        max_action_depth=4,
        allowed_actions=["move_task_dates"],
        allow_assignment_date_fallback=False,
        project_policies=_policies(),
    )

    assert document["input"]["root"] == str(settings.storage_root)
    assert document["planning"]["projects"][0] == {
        "project_id": "P1",
        "protection": "protected",
        "priority": 1,
        "max_finish_movement_calendar_days": 0,
    }
    assert document["risk"] == {
        "enabled": False,
        "iterations": None,
        "seed": None,
        "task_durations": [],
        "targets": [],
    }


def test_configuration_rejects_more_results_than_candidates(
    tmp_path, monkeypatch,
):
    settings = _settings(tmp_path, monkeypatch)

    with pytest.raises(ScenarioPlanningError, match="must not exceed"):
        build_configuration_document(
            settings,
            client_id="client-001",
            snapshot_id="snapshot-001",
            objective="protect_priority",
            scenario_count=3,
            candidate_limit=2,
            max_action_depth=4,
            allowed_actions=["move_task_dates"],
            allow_assignment_date_fallback=False,
            project_policies=_policies(),
        )


def test_project_policy_defaults_cover_each_project_once():
    projects = pd.DataFrame([
        {"ProjectID": "P2", "ProjectName": "Beta"},
        {"ProjectID": "P1", "ProjectName": "Alpha"},
        {"ProjectID": "P1", "ProjectName": "Alpha"},
    ])

    policies = default_project_policies(projects)

    assert policies["ProjectID"].tolist() == ["P1", "P2"]
    assert set(policies["Protection"]) == {"flexible"}
    assert set(policies["Priority"]) == {2}


def test_saved_runs_are_scoped_to_client_and_snapshot(
    tmp_path, monkeypatch,
):
    settings = _settings(tmp_path, monkeypatch)
    run_root = (
        settings.schedule_output_root / "client-001" / "runs" / "run-001"
    )
    run_root.mkdir(parents=True)
    (run_root / "run.json").write_text(json.dumps({
        "run_id": "run-001",
        "client_id": "client-001",
        "snapshot_id": "snapshot-001",
        "completed_at": "2026-10-04T10:00:00+00:00",
        "artifacts": {
            "configuration": "configuration.json",
            "generation_result": "generation.json",
        },
    }), encoding="utf-8")
    (run_root / "configuration.json").write_text(
        "{}", encoding="utf-8"
    )
    (run_root / "generation.json").write_text(
        "{}", encoding="utf-8"
    )

    assert len(list_generation_packages(
        settings, "client-001", "snapshot-001"
    )) == 1
    assert list_generation_packages(
        settings, "client-001", "another-snapshot"
    ) == []


def test_result_adapters_compare_baseline_and_selected_scenario():
    baseline_project = {
        "project_id": "P1",
        "project_name": "Alpha",
        "scheduled_start_date": "2026-01-01",
        "scheduled_finish_date": "2026-01-10",
    }
    scenario_project = {
        **baseline_project,
        "scheduled_finish_date": "2026-01-12",
    }
    candidate = {
        "action_depth": 1,
        "proposal": {
            "proposal_id": "proposal-1",
            "task_date_changes": [{"task_id": "T1"}],
            "resource_reassignments": [],
        },
        "result": {
            "feasibility_status": "feasible",
            "objective_metrics": [{"name": "changed_tasks", "value": 1}],
            "schedule": {"projects": [scenario_project]},
        },
    }
    generation = {
        "baseline": {"schedule": {"projects": [baseline_project]}},
        "selected_candidates": [candidate],
    }

    summary = candidate_summary_frame(generation)
    comparison = project_comparison_frame(generation, candidate)

    assert summary.iloc[0]["changed_tasks"] == 1
    assert comparison["Schedule"].tolist() == ["Baseline", "Scenario"]
    assert set(comparison["Finish movement (days)"]) == {2}


def test_result_adapters_explain_resource_reassignment():
    baseline_load = [{
        "resource_id": "R1",
        "start_date": "2026-11-10",
        "finish_date": "2026-11-20",
        "total_allocation": 140,
        "capacity": 100,
        "over_capacity": True,
    }]
    candidate = {
        "action_depth": 1,
        "proposal": {
            "proposal_id": "proposal-resource",
            "task_date_changes": [],
            "resource_reassignments": [{
                "task_id": "T1",
                "from_resource_id": "R1",
                "to_resource_id": "R2",
            }],
        },
        "result": {
            "feasibility_status": "feasible",
            "objective_metrics": [],
            "project_movements": [{"movement_calendar_days": 0}],
            "resource_load": [
                {
                    "resource_id": "R1",
                    "start_date": "2026-11-10",
                    "finish_date": "2026-11-20",
                    "total_allocation": 80,
                    "capacity": 100,
                    "over_capacity": False,
                },
                {
                    "resource_id": "R2",
                    "start_date": "2026-11-10",
                    "finish_date": "2026-11-20",
                    "total_allocation": 60,
                    "capacity": 100,
                    "over_capacity": False,
                },
            ],
            "schedule": {
                "assignments": [{
                    "assignment_id": "A1",
                    "task_id": "T1",
                    "source_resource_id": "R1",
                    "scheduled_resource_id": "R2",
                    "source_start_date": "2026-11-10",
                    "source_finish_date": "2026-11-20",
                    "scheduled_start_date": "2026-11-10",
                    "scheduled_finish_date": "2026-11-20",
                    "allocation": 60,
                }],
            },
        },
    }
    generation = {
        "baseline": {"resource_load": baseline_load},
        "selected_candidates": [candidate],
    }

    summary = candidate_summary_frame(generation)
    changes = assignment_change_frame(candidate)
    load = resource_load_comparison_frame(generation, candidate)
    impact = resource_impact_summary(generation, candidate)

    assert summary.iloc[0]["Primary action"] == "Reassign T1"
    assert summary.iloc[0]["Over-capacity intervals"] == "1 → 0"
    assert affected_resource_ids(generation, candidate) == ["R1", "R2"]
    assert set(load["ResourceID"]) == {"R1", "R2"}
    assert set(load["Schedule"]) == {"Baseline", "Scenario"}
    assert "facet" in scenario_resource_load_chart(load).to_dict()
    assert changes.iloc[0]["Change"] == "Resource"
    assert changes.iloc[0]["Scenario resource"] == "R2"
    assert impact == {
        "affected_resources": 2,
        "baseline_over_capacity_intervals": 1,
        "scenario_over_capacity_intervals": 0,
        "baseline_peak_affected_load": 140.0,
        "scenario_peak_affected_load": 80.0,
        "changed_assignments": 1,
        "maximum_finish_movement_days": 0,
    }
