import json
from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_workspace_renders_governed_snapshot(tmp_path, monkeypatch):
    snapshot_id = "snapshot-test"
    snapshot_root = tmp_path / "local-data" / "metadata" / "snapshots" / snapshot_id
    snapshot_root.mkdir(parents=True)
    (snapshot_root / "snapshot.json").write_text(json.dumps({
        "snapshot_id": snapshot_id,
        "observation_date": "2026-09-01",
        "datasets": {"projects": "projects.csv"},
    }), encoding="utf-8")
    (snapshot_root / "fitness.json").write_text(json.dumps({
        "capabilities": {"schedule": {
            "status": "fit",
            "blocking_conditions": [],
            "caveats": [],
            "unavailable_rules": [],
        }}
    }), encoding="utf-8")
    (snapshot_root / "findings.json").write_text(json.dumps({
        "findings": [{
            "finding_id": "SCH-1",
            "domain": "schedule",
            "severity": "high",
            "title": "Test condition",
            "description": "A deterministic test finding.",
            "rule_id": "SCH-TEST",
            "evidence": {"count": 1},
            "affected_entities": {"projects": ["P1"]},
            "supporting_artifacts": [],
        }]
    }), encoding="utf-8")
    monkeypatch.setenv("DATALAB_PLATFORM_PATH", str(tmp_path))
    monkeypatch.delenv("DATA_PLATFORM_STORAGE_ROOT", raising=False)

    app_path = Path(__file__).parents[1] / "app.py"
    app = AppTest.from_file(str(app_path), default_timeout=10).run()

    assert not app.exception
    assert app.session_state["selected_snapshot_id"] == snapshot_id
    assert any(metric.label == "Findings" and metric.value == "1" for metric in app.metric)

    for page in (
        "app_pages/evidence.py",
        "app_pages/findings.py",
        "app_pages/history.py",
        "app_pages/interpretations.py",
        "app_pages/run_lab.py",
    ):
        app.switch_page(page).run()
        assert not app.exception, page
