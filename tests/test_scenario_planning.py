import json
import subprocess
import sys

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
    constraint_violation_frame,
    cp_sat_integration_gate,
    default_project_policies,
    list_generation_packages,
    load_generation_package,
    observed_schedule_bounds,
    project_comparison_frame,
    resource_impact_summary,
    resource_load_comparison_frame,
    run_scenario_generation,
    schedule_platform_ready,
)


def _settings(tmp_path, monkeypatch):
    platform = tmp_path / "DataPlatform"
    (platform / "schemas").mkdir(parents=True)
    schedule = tmp_path / "SchedulePlatform"
    schema_root = schedule / "src" / "schedule_platform" / "schemas"
    schema_root.mkdir(parents=True)
    package_root = schema_root.parent
    (package_root / "__init__.py").write_text(
        '__version__ = "test-1.1"\n', encoding="utf-8"
    )
    (package_root / "cli.py").write_text(
        "from . import __version__\n"
        "if __name__ == '__main__':\n"
        "    print(f'schedule-platform {__version__}')\n",
        encoding="utf-8",
    )
    (schema_root / "analysis_config_v1.schema.json").write_text(
        json.dumps({
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "required": [
                "config_version", "input", "planning", "risk", "output"
            ],
            "properties": {
                "config_version": {"const": "1.1"},
                "input": {"type": "object"},
                "planning": {
                    "type": "object",
                    "required": ["planning_horizon"],
                    "properties": {
                        "planning_horizon": {
                            "type": "object",
                            "required": ["start_date", "end_date"],
                            "properties": {
                                "start_date": {
                                    "type": "string", "format": "date"
                                },
                                "end_date": {
                                    "type": "string", "format": "date"
                                },
                            },
                        },
                    },
                },
                "risk": {"type": "object"},
                "output": {"type": "object"},
            },
        }),
        encoding="utf-8",
    )
    monkeypatch.setenv("DATALAB_PLATFORM_PATH", str(platform))
    monkeypatch.setenv("SCHEDULE_PLATFORM_PATH", str(schedule))
    monkeypatch.setenv(
        "SCHEDULE_PLATFORM_OUTPUT_ROOT", str(tmp_path / "scenario-output")
    )
    monkeypatch.delenv("DATA_PLATFORM_STORAGE_ROOT", raising=False)
    # Keep the developer's .env interpreter out of synthetic CLI fixtures.
    monkeypatch.setenv("SCHEDULE_PLATFORM_PYTHON", sys.executable)
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


def test_schedule_platform_readiness_invokes_isolated_cli(
    tmp_path, monkeypatch,
):
    settings = _settings(tmp_path, monkeypatch)

    ready, message = schedule_platform_ready(settings)

    assert ready
    assert "schedule-platform test-1.1" in message
    assert str(settings.schedule_platform_python) in message


def test_schedule_platform_readiness_explains_missing_interpreter(
    tmp_path, monkeypatch,
):
    settings = _settings(tmp_path, monkeypatch)
    missing = tmp_path / "missing-environment" / "python.exe"
    monkeypatch.setenv("SCHEDULE_PLATFORM_PYTHON", str(missing))

    ready, message = schedule_platform_ready(settings)

    assert not ready
    assert str(missing) in message
    assert "SCHEDULE_PLATFORM_PYTHON" in message


def test_schedule_platform_python_prefers_its_own_environment(
    tmp_path, monkeypatch,
):
    settings = _settings(tmp_path, monkeypatch)
    monkeypatch.delenv("SCHEDULE_PLATFORM_PYTHON", raising=False)
    interpreter = (
        settings.schedule_platform_path
        / ".venv"
        / "Scripts"
        / "python.exe"
    )
    interpreter.parent.mkdir(parents=True)
    interpreter.write_text("", encoding="utf-8")

    assert settings.schedule_platform_python == interpreter.resolve()
    assert settings.schedule_platform_python != type(interpreter)(
        sys.executable
    ).resolve()


def test_cp_sat_stays_gated_without_public_cli_and_result_contracts(
    tmp_path, monkeypatch,
):
    settings = _settings(tmp_path, monkeypatch)

    enabled, message = cp_sat_integration_gate(settings)

    assert not enabled
    assert "configuration selector" in message
    assert "generate --backend cp-sat" in message
    assert "generation-result schema" in message


def test_cp_sat_gate_opens_only_when_all_public_contracts_exist(
    tmp_path, monkeypatch,
):
    settings = _settings(tmp_path, monkeypatch)
    schema_path = (
        settings.schedule_platform_path
        / "src"
        / "schedule_platform"
        / "schemas"
        / "analysis_config_v1.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    schema["$defs"] = {
        "planning": {
            "type": "object",
            "properties": {
                "generation_backend": {
                    "enum": ["bounded", "cp_sat"]
                },
            },
        },
    }
    schema_path.write_text(json.dumps(schema), encoding="utf-8")
    result_schema_path = schema_path.parent / "generation_result_v1.schema.json"
    result_schema_path.write_text(json.dumps({
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            name: {} for name in (
                "generation_backend",
                "solver_name",
                "solver_version",
                "solver_settings",
                "validation_succeeded",
            )
        },
    }), encoding="utf-8")
    cli_path = (
        settings.schedule_platform_path
        / "src"
        / "schedule_platform"
        / "cli.py"
    )
    cli_path.write_text(
        "import sys\n"
        "if 'generate' in sys.argv and '--help' in sys.argv:\n"
        "    print('generate --backend {bounded,cp-sat}')\n"
        "else:\n"
        "    print('schedule-platform test-1.1')\n",
        encoding="utf-8",
    )

    enabled, message = cp_sat_integration_gate(settings)

    assert enabled
    assert "required for integration testing" in message


def test_configuration_document_keeps_risk_disabled(
    tmp_path, monkeypatch,
):
    settings = _settings(tmp_path, monkeypatch)

    document = build_configuration_document(
        settings,
        client_id="client-001",
        snapshot_id="snapshot-001",
        objective="protect_priority",
        planning_horizon_start="2026-01-01",
        planning_horizon_end="2026-12-31",
        observed_schedule_start="2026-01-10",
        observed_schedule_end="2026-11-30",
        scenario_count=2,
        candidate_limit=50,
        max_action_depth=4,
        allowed_actions=["move_task_dates"],
        allow_assignment_date_fallback=False,
        project_policies=_policies(),
    )

    assert document["config_version"] == "1.1"
    assert document["input"]["root"] == str(settings.storage_root)
    assert document["planning"]["planning_horizon"] == {
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
    }
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


def test_generation_uses_configured_schedule_platform_interpreter(
    tmp_path, monkeypatch,
):
    from services import scenario_planning

    settings = _settings(tmp_path, monkeypatch)
    interpreter = tmp_path / "schedule-python" / "python.exe"
    monkeypatch.setenv("SCHEDULE_PLATFORM_PYTHON", str(interpreter))
    monkeypatch.setattr(
        scenario_planning,
        "schedule_platform_ready",
        lambda configured_settings: (True, "ready"),
    )
    document = build_configuration_document(
        settings,
        client_id="client-001",
        snapshot_id="snapshot-001",
        objective="protect_priority",
        planning_horizon_start="2026-01-01",
        planning_horizon_end="2026-12-31",
        observed_schedule_start="2026-01-10",
        observed_schedule_end="2026-11-30",
        scenario_count=2,
        candidate_limit=50,
        max_action_depth=4,
        allowed_actions=["move_task_dates"],
        allow_assignment_date_fallback=False,
        project_policies=_policies(),
    )
    captured_command = []

    def fake_run(command, **_kwargs):
        captured_command.extend(command)
        run_root = (
            settings.schedule_output_root
            / "client-001"
            / "runs"
            / "run-isolated"
        )
        run_root.mkdir(parents=True)
        (run_root / "run.json").write_text(json.dumps({
            "run_id": "run-isolated",
            "client_id": "client-001",
            "snapshot_id": "snapshot-001",
            "artifacts": {
                "configuration": "configuration.json",
                "generation_result": "generation.json",
            },
        }), encoding="utf-8")
        (run_root / "configuration.json").write_text(
            json.dumps(document), encoding="utf-8"
        )
        (run_root / "generation.json").write_text("{}", encoding="utf-8")
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps({"root": str(run_root)}) + "\n",
            stderr="",
        )

    monkeypatch.setattr(scenario_planning.subprocess, "run", fake_run)

    package = run_scenario_generation(
        settings, document, run_id="run-isolated"
    )

    assert captured_command[:4] == [
        str(interpreter.resolve()),
        "-m",
        "schedule_platform.cli",
        "generate",
    ]
    assert package["run"]["run_id"] == "run-isolated"


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
            planning_horizon_start="2026-01-01",
            planning_horizon_end="2026-12-31",
            observed_schedule_start="2026-01-10",
            observed_schedule_end="2026-11-30",
            scenario_count=3,
            candidate_limit=2,
            max_action_depth=4,
            allowed_actions=["move_task_dates"],
            allow_assignment_date_fallback=False,
            project_policies=_policies(),
        )


def test_configuration_rejects_reversed_planning_horizon(
    tmp_path, monkeypatch,
):
    settings = _settings(tmp_path, monkeypatch)

    with pytest.raises(ScenarioPlanningError, match="on or after"):
        build_configuration_document(
            settings,
            client_id="client-001",
            snapshot_id="snapshot-001",
            objective="protect_priority",
            planning_horizon_start="2026-12-31",
            planning_horizon_end="2026-01-01",
            observed_schedule_start="2026-01-10",
            observed_schedule_end="2026-11-30",
            scenario_count=2,
            candidate_limit=50,
            max_action_depth=4,
            allowed_actions=["move_task_dates"],
            allow_assignment_date_fallback=False,
            project_policies=_policies(),
        )


def test_configuration_rejects_horizon_outside_observed_schedule(
    tmp_path, monkeypatch,
):
    settings = _settings(tmp_path, monkeypatch)

    with pytest.raises(ScenarioPlanningError, match="must contain"):
        build_configuration_document(
            settings,
            client_id="client-001",
            snapshot_id="snapshot-001",
            objective="protect_priority",
            planning_horizon_start="2026-02-01",
            planning_horizon_end="2026-10-31",
            observed_schedule_start="2026-01-10",
            observed_schedule_end="2026-11-30",
            scenario_count=2,
            candidate_limit=50,
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


def test_observed_schedule_bounds_cover_projects_tasks_and_assignments():
    projects = pd.DataFrame([{
        "ForecastStartDate": "2026-01-05",
        "ForecastFinishDate": "2026-08-15",
    }])
    tasks = pd.DataFrame([{
        "ForecastStartDate": "2026-02-01",
        "ForecastFinishDate": "2026-10-20",
    }])
    assignments = pd.DataFrame([{
        "AssignmentStartDate": "2026-01-01",
        "AssignmentFinishDate": "2026-11-30",
    }])

    start, finish = observed_schedule_bounds(projects, tasks, assignments)

    assert start.isoformat() == "2026-01-01"
    assert finish.isoformat() == "2026-11-30"


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
    configuration = build_configuration_document(
        settings,
        client_id="client-001",
        snapshot_id="snapshot-001",
        objective="protect_priority",
        planning_horizon_start="2026-01-01",
        planning_horizon_end="2026-12-31",
        observed_schedule_start="2026-01-10",
        observed_schedule_end="2026-11-30",
        scenario_count=2,
        candidate_limit=50,
        max_action_depth=4,
        allowed_actions=["move_task_dates"],
        allow_assignment_date_fallback=False,
        project_policies=_policies(),
    )
    (run_root / "configuration.json").write_text(
        json.dumps(configuration), encoding="utf-8"
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


def test_generation_package_rejects_configuration_v1_0(
    tmp_path, monkeypatch,
):
    settings = _settings(tmp_path, monkeypatch)
    run_root = (
        settings.schedule_output_root / "client-001" / "runs" / "run-legacy"
    )
    run_root.mkdir(parents=True)
    (run_root / "run.json").write_text(json.dumps({
        "run_id": "run-legacy",
        "client_id": "client-001",
        "snapshot_id": "snapshot-001",
        "artifacts": {
            "configuration": "configuration.json",
            "generation_result": "generation.json",
        },
    }), encoding="utf-8")
    (run_root / "configuration.json").write_text(
        json.dumps({
            "config_version": "1.0",
            "input": {},
            "planning": {"planning_horizon": {
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
            }},
            "risk": {},
            "output": {},
        }),
        encoding="utf-8",
    )
    (run_root / "generation.json").write_text("{}", encoding="utf-8")

    with pytest.raises(ScenarioPlanningError, match="config_version"):
        load_generation_package(settings, run_root)


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


def test_constraint_violation_frame_promotes_planning_horizon_evidence():
    generation = {
        "evaluated_candidates": [{
            "proposal": {"proposal_id": "proposal-late"},
            "result": {
                "feasibility_status": "infeasible",
                "constraint_violations": [{
                    "code": "PLANNING-HORIZON-EXCEEDED",
                    "message": "A moved task finishes outside the horizon.",
                }],
            },
        }],
    }

    violations = constraint_violation_frame(generation)

    assert violations.to_dict("records") == [{
        "Proposal": "proposal-late",
        "Feasibility": "infeasible",
        "Code": "PLANNING-HORIZON-EXCEEDED",
        "Message": "A moved task finishes outside the horizon.",
    }]


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
