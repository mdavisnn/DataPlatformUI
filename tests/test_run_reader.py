import json

from config.settings import Settings
from services.run_reader import get_stage_statuses, list_runs, load_run


def test_lists_and_loads_runs_newest_first(tmp_path):
    runs = tmp_path / "local-data" / "metadata" / "runs"
    for run_id, started_at in (("older", "2026-01-01T00:00:00Z"), ("newer", "2026-02-01T00:00:00Z")):
        path = runs / run_id
        path.mkdir(parents=True)
        (path / "run.json").write_text(json.dumps({"run_id": run_id, "status": "success", "started_at": started_at, "stages": {"profiling": "completed"}}), encoding="utf-8")
    settings = Settings(tmp_path)
    assert [run.run_id for run in list_runs(settings)] == ["newer", "older"]
    assert load_run(settings, "older").status == "success"
    assert get_stage_statuses(settings, "older") == {"profiling": "completed"}


def test_skips_malformed_run_metadata(tmp_path):
    path = tmp_path / "metadata" / "runs" / "broken"
    path.mkdir(parents=True)
    (path / "run.json").write_text("not json", encoding="utf-8")
    assert list_runs(Settings(tmp_path)) == []

