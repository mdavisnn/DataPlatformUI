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


def write_plan_datasets(tmp_path, snapshot_id):
    snapshot_path = (
        tmp_path
        / "local-data"
        / "metadata"
        / "snapshots"
        / snapshot_id
        / "snapshot.json"
    )
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    snapshot["datasets"] = {
        "projects": f"{snapshot_id}/projects.csv",
        "tasks": f"{snapshot_id}/tasks.csv",
    }
    snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")

    processed = tmp_path / "local-data" / "processed" / snapshot_id
    processed.mkdir(parents=True)
    (processed / "projects.csv").write_text(
        "ProjectID,ProjectName,PortfolioID,ForecastStartDate,"
        "ForecastFinishDate\n"
        "P1,Alpha,PORT-A,2026-01-01,2026-03-31\n"
        "P2,Beta,PORT-B,2026-02-01,2026-04-30\n",
        encoding="utf-8",
    )
    (processed / "tasks.csv").write_text(
        "TaskID,ProjectID,TaskName,ForecastStartDate,"
        "ForecastFinishDate,IsMilestone\n"
        "T1,P1,Design,2026-01-01,2026-01-31,false\n"
        "T2,P2,Build,2026-02-01,2026-04-15,false\n",
        encoding="utf-8",
    )


def test_workspace_renders_governed_snapshot(tmp_path, monkeypatch):
    snapshot_id = "snapshot-test"
    write_snapshot(tmp_path, "client-001", snapshot_id, "2026-09-01")
    monkeypatch.setenv("DATALAB_PLATFORM_PATH", str(tmp_path))
    monkeypatch.delenv("DATA_PLATFORM_STORAGE_ROOT", raising=False)

    app_path = Path(__file__).parents[1] / "app.py"
    app = AppTest.from_file(str(app_path), default_timeout=10).run()

    assert not app.exception
    assert app.session_state["selected_snapshot_id"] == snapshot_id
    assert any(button.label == "Exit Data Lab" for button in app.button)
    assert any(metric.label == "Findings" and metric.value == "1" for metric in app.metric)

    for page in (
        "app_pages/evidence.py",
        "app_pages/findings.py",
        "app_pages/plan.py",
        "app_pages/history.py",
        "app_pages/interpretations.py",
        "app_pages/run_lab.py",
    ):
        app.switch_page(page).run()
        assert not app.exception, page


def test_plan_filters_portfolio_and_drills_into_project(
    tmp_path,
    monkeypatch,
):
    snapshot_id = "snapshot-plan"
    write_snapshot(tmp_path, "client-001", snapshot_id, "2026-09-01")
    write_plan_datasets(tmp_path, snapshot_id)
    monkeypatch.setenv("DATALAB_PLATFORM_PATH", str(tmp_path))
    monkeypatch.delenv("DATA_PLATFORM_STORAGE_ROOT", raising=False)

    app_path = Path(__file__).parents[1] / "app.py"
    app = AppTest.from_file(str(app_path), default_timeout=10).run()
    app.switch_page("app_pages/plan.py").run()

    assert not app.exception
    portfolio = app.selectbox(key=f"plan_portfolio_{snapshot_id}")
    portfolio.set_value("PORT-A").run()
    assert not app.exception
    projects_metric = next(
        metric
        for metric in app.metric
        if metric.label == "Projects plotted"
    )
    assert projects_metric.value == "1"

    project = app.selectbox(
        key=f"plan_project_{snapshot_id}_PORT-A"
    )
    project.set_value("P1").run()

    assert not app.exception
    assert any(header.value == "Alpha · P1" for header in app.header)
    assert any(
        metric.label == "Tasks plotted" and metric.value == "1"
        for metric in app.metric
    )


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


def test_exit_button_requests_server_shutdown(tmp_path, monkeypatch):
    snapshot_id = "snapshot-test"
    write_snapshot(tmp_path, "client-001", snapshot_id, "2026-09-01")
    monkeypatch.setenv("DATALAB_PLATFORM_PATH", str(tmp_path))
    monkeypatch.delenv("DATA_PLATFORM_STORAGE_ROOT", raising=False)

    from components import exit_control

    shutdown_requests = []
    monkeypatch.setattr(
        exit_control,
        "request_streamlit_shutdown",
        lambda: shutdown_requests.append(True),
    )

    app_path = Path(__file__).parents[1] / "app.py"
    app = AppTest.from_file(str(app_path), default_timeout=10).run()
    app.button(key="exit_application").click().run()

    assert shutdown_requests == [True]
    assert not app.exception


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
    inspect_button = next(
        button
        for button in app.button
        if button.label == "Inspect staged evidence"
    )
    assert not inspect_button.disabled
