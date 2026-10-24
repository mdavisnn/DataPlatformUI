from copy import deepcopy
from datetime import date

import pandas as pd
import pytest

from components.scenario_charts import project_finish_movement_chart
from services.scenario_presentation import (
    draft_from_planning, finish_movement_frame, generation_guidance,
    option_story, overloaded_resource_days, planning_from_editors, planning_signature,
)
from tests.test_app import app_for, write_snapshot


def saved_package(tmp_path):
    planning = {
        "objective": "minimise_changes", "scenario_count": 2,
        "candidate_limit": 250, "max_action_depth": 5,
        "planning_horizon": {"start_date": "2026-01-01", "end_date": "2026-12-31"},
        "allowed_actions": ["move_task_dates", "reassign_resource"],
        "allow_assignment_date_fallback": True,
        "projects": [
            {"project_id": "P1", "protection": "protected", "priority": 1, "max_finish_movement_calendar_days": 0},
            {"project_id": "P2", "protection": "flexible", "priority": 3, "max_finish_movement_calendar_days": 14},
        ],
        "resource_substitutions": [{"task_id": "T2", "from_resource_id": "R1", "to_resource_id": "R2"}],
        "targets": [{"target_id": "beta-date", "type": "project_finish", "entity_id": "P2",
                     "target_date": "2026-05-15", "treatment": "report_only"}],
    }
    baseline_projects = [
        {"project_id": "P1", "project_name": "Alpha", "scheduled_start_date": "2026-01-01", "scheduled_finish_date": "2026-03-31"},
        {"project_id": "P2", "project_name": "Beta", "scheduled_start_date": "2026-02-01", "scheduled_finish_date": "2026-04-30"},
    ]
    candidates = []
    for index, finish in enumerate(("2026-05-05", "2026-04-30")):
        projects = deepcopy(baseline_projects)
        projects[1]["scheduled_finish_date"] = finish
        candidates.append({
            "action_depth": 1, "state_fingerprint": f"state-{index}",
            "proposal": {"proposal_id": f"proposal-{index}", "task_date_changes": [{
                "task_id": "T2", "proposed_start_date": "2026-02-06", "proposed_finish_date": "2026-04-20",
            }], "resource_reassignments": []},
            "result": {
                "feasibility_status": "feasible", "resource_load": [],
                "schedule": {"projects": projects, "assignments": []},
                "date_deltas": [{"entity_type": "task", "entity_id": "T2", "origin": "direct"}],
                "constraint_violations": [],
            }, "target_outcomes": [],
        })
    return {
        "root": tmp_path / "output" / "run-discussion",
        "run": {"run_id": "run-discussion", "client_id": "client-001", "snapshot_id": "discussion",
                "configuration_fingerprint": "sha256:discussion", "engine_version": "test-engine", "rule_set_version": "test-rules"},
        "configuration": {"config_version": "1.1", "planning": planning},
        "generation": {
            "status": "complete", "search_truncated": False, "candidates_evaluated": 2,
            "baseline": {"status": "available", "schedule": {"projects": baseline_projects},
                         "resource_load": [{"resource_id": "R1", "start_date": "2026-02-01", "finish_date": "2026-02-10", "over_capacity": True,
                                            "total_allocation": 140, "capacity": 100}]},
            "selected_candidates": candidates, "evaluated_candidates": candidates,
        },
    }


def test_pressure_measure_is_inclusive_and_independent_of_interval_partitioning():
    period = {"resource_id": "R1", "over_capacity": True}
    whole = [{**period, "start_date": "2026-01-01", "finish_date": "2026-01-10"}]
    split = [
        {**period, "start_date": "2026-01-01", "finish_date": "2026-01-05"},
        {**period, "start_date": "2026-01-05", "finish_date": "2026-01-10"},
    ]
    assert overloaded_resource_days(whole) == overloaded_resource_days(split) == 10
    assert overloaded_resource_days(None) is None
    assert overloaded_resource_days([]) == 0


def test_option_story_explains_trade_off_and_retains_protected_projects(tmp_path):
    package = saved_package(tmp_path)
    generation = package["generation"]
    planning = package["configuration"]["planning"]
    option = generation["selected_candidates"][0]
    story = option_story(generation, option, planning, {"T2": "Build"})
    assert story["baseline_overload_days"] == 10
    assert story["scenario_overload_days"] == 0
    assert story["delayed_projects"] == 1
    assert "Beta" in story["trade_off"] and "5 calendar days" in story["trade_off"]
    assert "protected project finish dates are unchanged" in story["protection"]
    assert "Build" in story["actions"][0]
    frame = finish_movement_frame(generation, option, planning)
    assert frame["Movement (days)"].tolist() == [0, 5]
    assert frame["Protection"].tolist() == ["protected", "flexible"]
    assert len(project_finish_movement_chart(frame).to_dict()["layer"]) == 2
    option["result"].pop("resource_load")
    option["result"]["schedule"]["projects"].pop()
    missing = option_story(generation, option, planning)
    assert missing["scenario_overload_days"] is None
    assert missing["delayed_projects"] is None
    assert "not fully recorded" in missing["trade_off"]


def test_restored_assumptions_round_trip_all_planning_fields(tmp_path):
    planning = saved_package(tmp_path)["configuration"]["planning"]
    projects = pd.DataFrame([{"ProjectID": "P1", "ProjectName": "Alpha"}, {"ProjectID": "P2", "ProjectName": "Beta"}])
    restored = draft_from_planning(planning, projects)
    scalar_values = {key: value for key, value in planning.items() if key not in ("projects", "resource_substitutions", "targets")}
    round_trip = planning_from_editors(scalar_values, restored["policies"], restored["substitutions"], restored["targets"])
    assert planning_signature(round_trip) == planning_signature(planning)
    assert restored["targets"].iloc[0]["TargetDate"] == date(2026, 5, 15)
    restored["planning"]["projects"][0]["priority"] = 3
    assert planning["projects"][0]["priority"] == 1


@pytest.mark.parametrize("status,headline", [
    ("input_not_fit", "Baseline needs attention"),
    ("no_change_needed", "No change needed under these assumptions"),
    ("no_feasible_scenario", "No feasible option found"),
    ("search_truncated", "Search limit reached"),
])
def test_generation_states_offer_distinct_guidance(status, headline):
    assert generation_guidance({"status": status})[0] == headline


def workspace(tmp_path, monkeypatch, *, ready=True):
    from services import scenario_planning

    package = saved_package(tmp_path)
    write_snapshot(tmp_path, "client-001", "discussion", "2026-09-01")
    resources_path = tmp_path / "local-data" / "processed" / "client-001" / "snapshots" / "discussion" / "resources.csv"
    resources_path.write_text(
        resources_path.read_text(encoding="utf-8") + "R2,Backup planner,Planner,Controls,100\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(scenario_planning, "schedule_platform_ready", lambda settings: (ready, "test environment"))
    packages = [package]
    monkeypatch.setattr(scenario_planning, "list_generation_packages", lambda *args: packages)
    app = app_for(tmp_path, monkeypatch)
    app.switch_page("app_pages/scenario_planning.py").run()
    assert not app.exception
    return app, package, packages


PREFIX = "scenario_client-001_discussion"


def test_saved_option_cards_and_charts_work_without_generation_environment(tmp_path, monkeypatch):
    app, package, _ = workspace(tmp_path, monkeypatch, ready=False)
    assert not app.number_input  # Configuration and technical evidence start collapsed.
    assert any("Highest-ranked option found" in item.value for item in app.caption)
    app.button(key=f"{PREFIX}_run-discussion_option_1").click().run()
    assert not app.exception
    assert any(item.value == "Option B · what this means" for item in app.subheader)
    app.segmented_control(key=f"{PREFIX}_run-discussion_view").set_value("Finish dates").run()
    assert not app.exception
    frame = app.dataframe[0].value
    assert frame["Project"].tolist() == ["Alpha", "Beta"]
    assert frame["Movement (days)"].tolist() == [0, 0]
    assert package["generation"]["selected_candidates"][0]["result"]["schedule"]["projects"][1]["scheduled_finish_date"] == "2026-05-05"


def test_reuse_restores_assumptions_and_marks_live_draft_edits(tmp_path, monkeypatch):
    app, package, _ = workspace(tmp_path, monkeypatch)
    app.button(key=f"{PREFIX}_reuse").click().run()
    assert not app.exception
    assert any("Draft assumptions match" in item.value for item in app.caption)
    assert planning_signature(app.session_state[f"{PREFIX}_draft"]) == planning_signature(package["configuration"]["planning"])
    app.toggle(key=f"{PREFIX}_advanced").set_value(True).run()
    assert app.number_input(key=f"{PREFIX}_candidate_limit").value == 250
    assert app.checkbox(key=f"{PREFIX}_allow_assignment_date_fallback").value is True
    app.date_input(key=f"{PREFIX}_horizon_end").set_value(date(2027, 1, 31)).run()
    assert not app.exception
    assert any("Draft assumptions differ" in item.value for item in app.warning)
    app.session_state[f"{PREFIX}_configuration_open"] = False
    app.run()
    assert any("Draft assumptions differ" in item.value for item in app.warning)
    app.session_state[f"{PREFIX}_configuration_open"] = True
    app.run()
    assert not app.exception
    assert app.date_input(key=f"{PREFIX}_horizon_end").value == date(2027, 1, 31)
    assert app.session_state[f"{PREFIX}_draft"]["targets"] == package["configuration"]["planning"]["targets"]


def test_optional_boundaries_survive_being_hidden(tmp_path, monkeypatch):
    app, package, _ = workspace(tmp_path, monkeypatch)
    app.button(key=f"{PREFIX}_reuse").click().run()
    app.toggle(key=f"{PREFIX}_boundaries").set_value(True).run()
    assert not app.exception
    # AppTest cannot edit grids; inject the same row delta the browser submits.
    revision = app.session_state[f"{PREFIX}_editor_revision"]
    app.session_state[f"{PREFIX}_targets_{revision}"] = {
        "edited_rows": {0: {"TargetID": "client-deadline"}}, "added_rows": [], "deleted_rows": [],
    }
    app.run()
    assert app.session_state[f"{PREFIX}_draft"]["targets"][0]["target_id"] == "client-deadline"
    app.toggle(key=f"{PREFIX}_boundaries").set_value(False).run()
    app.toggle(key=f"{PREFIX}_boundaries").set_value(True).run()
    assert not app.exception
    assert app.session_state[f"{PREFIX}_draft"]["targets"][0]["target_id"] == "client-deadline"
    assert package["configuration"]["planning"]["targets"][0]["target_id"] == "beta-date"


def test_generate_submits_edited_v1_1_contract_and_selects_new_saved_run(tmp_path, monkeypatch):
    from services import scenario_planning

    app, original, packages = workspace(tmp_path, monkeypatch)
    captured = []
    monkeypatch.setattr(scenario_planning, "_configuration_schema", lambda settings: {
        "type": "object", "properties": {"config_version": {"const": "1.1"}},
    })

    def generate(settings, configuration):
        captured.append(deepcopy(configuration))
        generated = deepcopy(original)
        generated["run"]["run_id"] = "run-new"
        generated["configuration"] = deepcopy(configuration)
        packages.insert(0, generated)
        return generated

    monkeypatch.setattr(scenario_planning, "run_scenario_generation", generate)
    app.button(key=f"{PREFIX}_reuse").click().run()
    app.date_input(key=f"{PREFIX}_horizon_end").set_value(date(2027, 1, 31)).run()
    assert not app.exception
    app.button(key=f"{PREFIX}_generate").click().run()

    assert not app.exception
    assert len(captured) == 1
    assert captured[0]["config_version"] == "1.1"
    assert captured[0]["risk"]["enabled"] is False
    assert captured[0]["planning"]["planning_horizon"]["end_date"] == "2027-01-31"
    assert captured[0]["planning"]["projects"] == original["configuration"]["planning"]["projects"]
    assert captured[0]["planning"]["targets"] == original["configuration"]["planning"]["targets"]
    assert app.selectbox(key=f"{PREFIX}_active_run").value == "run-new"
    assert not app.number_input  # Successful generation closes configuration.
    assert any("New results are saved" in item.value for item in app.success)
