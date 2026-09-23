import json
from pathlib import Path

from streamlit.testing.v1 import AppTest


def _write_json(path, document):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document), encoding="utf-8")


def write_snapshot(tmp_path, client_id, snapshot_id, observation_date):
    storage = tmp_path / "local-data"
    _write_json(
        storage / "metadata" / client_id / "client.json",
        {"format_version": "1.0", "client_id": client_id},
    )
    snapshot_root = (
        storage / "metadata" / client_id / "snapshots" / snapshot_id
    )
    processed = (
        storage / "processed" / client_id / "snapshots" / snapshot_id
    )
    curated = (
        storage / "curated" / client_id / "snapshots" / snapshot_id
    )
    datasets = {
        "projects": f"{client_id}/snapshots/{snapshot_id}/projects.csv",
        "tasks": f"{client_id}/snapshots/{snapshot_id}/tasks.csv",
    }
    _write_json(snapshot_root / "snapshot.json", {
        "format_version": "1.0",
        "client_id": client_id,
        "snapshot_id": snapshot_id,
        "run_id": f"run-{snapshot_id}",
        "observation_date": observation_date,
        "datasets": datasets,
    })
    _write_json(snapshot_root / "fitness.json", {
        "format_version": "1.0",
        "client_id": client_id,
        "snapshot_id": snapshot_id,
        "capabilities": {
            name: {
                "status": "fit",
                "blocking_conditions": [],
                "caveats": [],
                "unavailable_rules": [],
            }
            for name in (
                "data", "schedule", "resource", "portfolio", "reporting"
            )
        },
    })
    finding = {
        "finding_id": "SCH-1",
        "domain": "schedule",
        "severity": "high",
        "title": "Test condition",
        "description": "A deterministic test finding.",
        "rule_id": "SCH-TEST",
        "evidence": {"count": 1},
        "affected_entities": {"projects": ["P1"]},
        "supporting_artifacts": [],
    }
    _write_json(snapshot_root / "findings.json", {
        "format_version": "1.0",
        "client_id": client_id,
        "snapshot_id": snapshot_id,
        "finding_count": 1,
        "counts_by_domain": {"schedule": 1},
        "counts_by_severity": {"high": 1},
        "findings": [finding],
    })
    project_health_reference = (
        f"curated/{client_id}/snapshots/{snapshot_id}/"
        "overview/project_health.csv"
    )
    _write_json(snapshot_root / "diagnosis.json", {
        "format_version": "1.0",
        "client_id": client_id,
        "snapshot_id": snapshot_id,
        "execution_status": "success",
        "project_health_object": project_health_reference,
        "summary": {
            "portfolio_scale": {
                "projects": 2,
                "tasks": 2,
                "milestones": 0,
                "resources": 1,
                "assignments": 2,
                "dependencies": 0,
            },
            "findings": {
                "total": 1,
                "projects_affected": 1,
                "by_domain": {"schedule": 1},
                "by_severity": {"high": 1},
            },
            "diagnostics": {
                "total": 5,
                "completed": 5,
                "skipped": 0,
                "failed": 0,
            },
            "fitness": {
                "blocking_conditions": 0,
                "caveats": 0,
                "unavailable_rules": 0,
            },
        },
    })
    processed.mkdir(parents=True, exist_ok=True)
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
    health = curated / "overview" / "project_health.csv"
    health.parent.mkdir(parents=True, exist_ok=True)
    health.write_text(
        "ProjectID,ProjectName,PortfolioID,ProgrammeID,LifecycleStatus,"
        "RAGStatus,TaskCount,PortfolioStatus,ScheduleStatus,"
        "ResourceStatus,ReportingStatus,DependencyStatus,DataFitness,"
        "FindingCount,HighFindings,MediumFindings,LowFindings,FindingIDs\n"
        "P1,Alpha,PORT-A,,Active,Amber,1,No finding,Significant,"
        "No finding,No finding,Not assessed,Fit,1,1,0,0,SCH-1\n"
        "P2,Beta,PORT-B,,Active,Green,1,No finding,No finding,"
        "No finding,No finding,Not assessed,Fit,0,0,0,0,\n",
        encoding="utf-8",
    )


def app_for(tmp_path, monkeypatch):
    monkeypatch.setenv("DATALAB_PLATFORM_PATH", str(tmp_path))
    monkeypatch.delenv("DATA_PLATFORM_STORAGE_ROOT", raising=False)
    app_path = Path(__file__).parents[1] / "app.py"
    return AppTest.from_file(str(app_path), default_timeout=10).run()


def test_workspace_renders_governed_snapshot(tmp_path, monkeypatch):
    snapshot_id = "snapshot-test"
    write_snapshot(tmp_path, "client-001", snapshot_id, "2026-09-01")

    app = app_for(tmp_path, monkeypatch)

    assert not app.exception
    assert app.session_state["selected_snapshot_id"] == snapshot_id
    assert any(
        button.label == "Exit Data Lab" for button in app.button
    )
    assert any(
        metric.label == "Findings" and metric.value == "1"
        for metric in app.metric
    )
    for page in (
        "app_pages/evidence.py",
        "app_pages/findings.py",
        "app_pages/project_health.py",
        "app_pages/plan.py",
        "app_pages/history.py",
        "app_pages/interpretations.py",
        "app_pages/run_lab.py",
    ):
        app.switch_page(page).run()
        assert not app.exception, page


def test_project_health_uses_governed_matrix(tmp_path, monkeypatch):
    snapshot_id = "snapshot-health"
    write_snapshot(tmp_path, "client-001", snapshot_id, "2026-09-01")
    app = app_for(tmp_path, monkeypatch)

    app.switch_page("app_pages/project_health.py").run()

    assert not app.exception
    assert any(
        metric.label == "Projects shown" and metric.value == "2"
        for metric in app.metric
    )
    assert len(app.dataframe[0].value) == 2
    assert app.selectbox(key=f"health_project_{snapshot_id}").value == "P1"
    assert any(
        item.value == "Project findings" for item in app.subheader
    )


def test_plan_filters_portfolio_and_drills_into_project(
    tmp_path, monkeypatch,
):
    snapshot_id = "snapshot-plan"
    write_snapshot(tmp_path, "client-001", snapshot_id, "2026-09-01")
    app = app_for(tmp_path, monkeypatch)
    app.switch_page("app_pages/plan.py").run()

    portfolio = app.selectbox(key=f"plan_portfolio_{snapshot_id}")
    portfolio.set_value("PORT-A").run()
    assert not app.exception
    assert any(
        metric.label == "Projects plotted" and metric.value == "1"
        for metric in app.metric
    )
    app.selectbox(
        key=f"plan_project_{snapshot_id}_PORT-A"
    ).set_value("P1").run()
    assert not app.exception
    assert any(
        metric.label == "Tasks plotted" and metric.value == "1"
        for metric in app.metric
    )


def test_client_selection_scopes_observations(tmp_path, monkeypatch):
    write_snapshot(tmp_path, "alpha", "snapshot-alpha", "2026-09-01")
    write_snapshot(
        tmp_path, "alpha", "snapshot-alpha-old", "2026-08-01"
    )
    write_snapshot(tmp_path, "beta", "snapshot-beta", "2026-09-01")
    app = app_for(tmp_path, monkeypatch)

    assert app.session_state["selected_client_id"] == "alpha"
    app.selectbox(key="client_selector").select("beta").run()
    assert not app.exception
    assert app.session_state["selected_client_id"] == "beta"
    assert app.session_state["selected_snapshot_id"] == "snapshot-beta"


def test_exit_button_requests_server_shutdown(tmp_path, monkeypatch):
    write_snapshot(
        tmp_path, "client-001", "snapshot-test", "2026-09-01"
    )
    from components import exit_control

    shutdown_requests = []
    monkeypatch.setattr(
        exit_control,
        "request_streamlit_shutdown",
        lambda: shutdown_requests.append(True),
    )
    app = app_for(tmp_path, monkeypatch)
    app.button(key="exit_application").click().run()

    assert shutdown_requests == [True]
    assert not app.exception


def test_raw_only_client_can_open_inspection(tmp_path, monkeypatch):
    inbox = tmp_path / "local-data" / "raw" / "new-client"
    inbox.mkdir(parents=True)
    (inbox / "projects.csv").write_text(
        "ProjectID\nP1\n", encoding="utf-8"
    )
    app = app_for(tmp_path, monkeypatch)
    app.switch_page("app_pages/run_lab.py").run()

    assert not app.exception
    assert app.session_state["selected_client_id"] == "new-client"
    inspect_button = next(
        button for button in app.button
        if button.label == "Inspect raw evidence"
    )
    assert not inspect_button.disabled
