import json
from pathlib import Path

from streamlit.testing.v1 import AppTest


def write_snapshot(tmp_path, client_id, snapshot_id, observation_date):
    snapshot_root = tmp_path / "local-data" / "metadata" / "snapshots" / snapshot_id
    snapshot_root.mkdir(parents=True)
    (snapshot_root / "snapshot.json").write_text(json.dumps({
        "client_id": client_id,
        "snapshot_id": snapshot_id,
        "observation_date": observation_date,
        "datasets": {"projects": "projects.csv"},
    }), encoding="utf-8")
    (snapshot_root / "fitness.json").write_text(json.dumps({
        "client_id": client_id,
        "snapshot_id": snapshot_id,
        "capabilities": {"schedule": {
            "status": "fit",
            "blocking_conditions": [],
            "caveats": [],
            "unavailable_rules": [],
        }}
    }), encoding="utf-8")
    (snapshot_root / "findings.json").write_text(json.dumps({
        "client_id": client_id,
        "snapshot_id": snapshot_id,
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


def test_workspace_renders_governed_snapshot(tmp_path, monkeypatch):
    snapshot_id = "snapshot-test"
    write_snapshot(tmp_path, "client-001", snapshot_id, "2026-09-01")
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


def test_client_selection_scopes_observations(tmp_path, monkeypatch):
    write_snapshot(tmp_path, "alpha", "snapshot-alpha", "2026-09-01")
    write_snapshot(tmp_path, "alpha", "snapshot-alpha-old", "2026-08-01")
    write_snapshot(tmp_path, "beta", "snapshot-beta", "2026-09-01")
    monkeypatch.setenv("DATALAB_PLATFORM_PATH", str(tmp_path))
    monkeypatch.delenv("DATA_PLATFORM_STORAGE_ROOT", raising=False)

    app_path = Path(__file__).parents[1] / "app.py"
    app = AppTest.from_file(str(app_path), default_timeout=10).run()

    assert not app.exception
    assert app.session_state["selected_client_id"] == "alpha"
    assert app.session_state["selected_snapshot_id"] == "snapshot-alpha"

    app.selectbox(key="observation_selector_alpha").select(
        "2026-08-01 | snapshot-alpha-old"
    ).run()
    assert app.session_state["selected_snapshot_id"] == "snapshot-alpha-old"

    app.selectbox(key="client_selector").select("beta").run()

    assert not app.exception
    assert app.session_state["selected_client_id"] == "beta"
    assert app.session_state["selected_snapshot_id"] == "snapshot-beta"
    assert app.selectbox(key="observation_selector_beta").options == [
        "2026-09-01 | snapshot-beta"
    ]

    app.selectbox(key="client_selector").select("alpha").run()

    assert app.session_state["selected_client_id"] == "alpha"
    assert app.session_state["selected_snapshot_id"] == "snapshot-alpha"


def test_staged_only_client_can_open_inspection(tmp_path, monkeypatch):
    staged = tmp_path / "local-data" / "staged" / "new-client"
    staged.mkdir(parents=True)
    (staged / "projects.csv").write_text("ProjectID\nP1\n", encoding="utf-8")
    monkeypatch.setenv("DATALAB_PLATFORM_PATH", str(tmp_path))
    monkeypatch.delenv("DATA_PLATFORM_STORAGE_ROOT", raising=False)

    app_path = Path(__file__).parents[1] / "app.py"
    app = AppTest.from_file(str(app_path), default_timeout=10).run()
    app.switch_page("app_pages/run_lab.py").run()

    assert not app.exception
    assert app.session_state["selected_client_id"] == "new-client"
    assert app.button[0].label == "Inspect staged evidence"
    assert not app.button[0].disabled
