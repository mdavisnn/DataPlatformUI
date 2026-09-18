import json

from config.settings import Settings
from services.output_reader import (
    load_analysis_outputs,
    load_curation_outputs,
    load_processed_outputs,
    load_profiles,
    load_validation_errors,
)


def test_loads_run_specific_outputs(tmp_path):
    run_id = "demo-001"
    run = tmp_path / "local-data" / "metadata" / "runs" / run_id
    (run / "profiles").mkdir(parents=True)
    (run / "curation").mkdir()
    processed = tmp_path / "local-data" / "processed" / "history" / "projects" / run_id
    curated = tmp_path / "local-data" / "curated" / "history" / "portfolio" / run_id
    processed.mkdir(parents=True)
    curated.mkdir(parents=True)

    (run / "profiles" / "projects.json").write_text(json.dumps({"row_count": 1}), encoding="utf-8")
    (run / "processing.json").write_text(json.dumps({"datasets": [{"dataset": "projects", "history_key": f"history/projects/{run_id}/projects.csv", "rows_out": 1}]}), encoding="utf-8")
    (run / "curation" / "portfolio.json").write_text(json.dumps({"curated_object": f"history/portfolio/{run_id}/portfolio.csv", "rows_written": 1, "validation_quality_status": "PASS"}), encoding="utf-8")
    (run / "validation_errors.csv").write_text("rule,message\nrequired,missing\n", encoding="utf-8")
    (processed / "projects.csv").write_text("id\nP1\n", encoding="utf-8")
    (curated / "portfolio.csv").write_text("id\nP1\n", encoding="utf-8")

    settings = Settings(tmp_path)
    assert load_profiles(settings, run_id)["projects"]["row_count"] == 1
    assert len(load_processed_outputs(settings, run_id)[0].data) == 1
    assert len(load_curation_outputs(settings, run_id)[0].data) == 1
    assert len(load_validation_errors(settings, run_id).data) == 1


def test_catalogues_available_and_missing_analysis_outputs(tmp_path):
    curated = tmp_path / "local-data" / "curated"
    curated.mkdir(parents=True)
    (curated / "resource_conflicts.csv").write_text("resource_id\nR1\n", encoding="utf-8")

    outputs = load_analysis_outputs(Settings(tmp_path))
    conflicts = next(output for output in outputs if output.name == "resource_conflicts.csv")
    history = next(output for output in outputs if output.name == "project_changes.csv")
    assert conflicts.available
    assert not history.available
