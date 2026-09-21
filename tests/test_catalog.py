import json

from config.settings import Settings
from services.catalog import (
    Catalogue,
    findings_frame,
    flatten_fitness,
    validate_client_id,
)


def store_text(root, area, key, value):
    path = root / "local-data" / area / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def store_json(root, key, value):
    store_text(root, "metadata", key, json.dumps(value))


def catalogue_for(tmp_path, monkeypatch):
    monkeypatch.delenv("DATA_PLATFORM_STORAGE_ROOT", raising=False)
    return Catalogue(Settings(tmp_path))


def test_catalogue_lists_and_orders_snapshots_by_observation_date(tmp_path, monkeypatch):
    store_json(tmp_path, "snapshots/older/snapshot.json", {
        "client_id": "client-001",
        "snapshot_id": "older",
        "observation_date": "2026-01-31",
    })
    store_json(tmp_path, "snapshots/newer/snapshot.json", {
        "client_id": "client-001",
        "snapshot_id": "newer",
        "observation_date": "2026-02-28",
    })

    snapshots = catalogue_for(tmp_path, monkeypatch).list_snapshots("client-001")

    assert [item["snapshot_id"] for item in snapshots] == ["newer", "older"]


def test_snapshot_bundle_tolerates_optional_products(tmp_path, monkeypatch):
    store_json(tmp_path, "snapshots/one/snapshot.json", {
        "client_id": "client-001",
        "snapshot_id": "one",
    })

    assert catalogue_for(tmp_path, monkeypatch).snapshot_bundle(
        "one", "client-001"
    ) == {
        "snapshot": {"client_id": "client-001", "snapshot_id": "one"},
        "fitness": {},
        "diagnosis": {},
        "findings": {},
    }


def test_catalogue_lists_clients_and_scopes_runs_and_snapshots(tmp_path, monkeypatch):
    store_json(tmp_path, "runs/run-alpha/run_summary.json", {
        "client_id": "alpha",
        "run_id": "run-alpha",
    })
    store_json(tmp_path, "runs/run-beta/run_summary.json", {
        "client_id": "beta",
        "run_id": "run-beta",
    })
    store_json(tmp_path, "snapshots/snapshot-alpha/snapshot.json", {
        "client_id": "alpha",
        "snapshot_id": "snapshot-alpha",
        "observation_date": "2026-08-31",
    })
    store_json(tmp_path, "snapshots/snapshot-beta/snapshot.json", {
        "client_id": "beta",
        "snapshot_id": "snapshot-beta",
        "observation_date": "2026-08-31",
    })

    catalogue = catalogue_for(tmp_path, monkeypatch)

    assert catalogue.list_clients() == ["alpha", "beta"]
    assert [item["run_id"] for item in catalogue.list_runs("alpha")] == [
        "run-alpha"
    ]
    assert [
        item["snapshot_id"] for item in catalogue.list_snapshots("beta")
    ] == ["snapshot-beta"]


def test_catalogue_includes_valid_staged_only_clients(tmp_path, monkeypatch):
    (tmp_path / "local-data" / "staged" / "new-client").mkdir(parents=True)
    (tmp_path / "local-data" / "staged" / "Invalid Client").mkdir()

    assert catalogue_for(tmp_path, monkeypatch).list_clients() == ["new-client"]


def test_catalogue_scopes_history_and_interpretations(tmp_path, monkeypatch):
    store_json(tmp_path, "snapshots/snapshot-alpha/snapshot.json", {
        "client_id": "alpha",
        "snapshot_id": "snapshot-alpha",
    })
    store_json(tmp_path, "snapshots/snapshot-beta/snapshot.json", {
        "client_id": "beta",
        "snapshot_id": "snapshot-beta",
    })
    store_json(tmp_path, "comparisons/comparison-alpha/comparison.json", {
        "client_id": "alpha",
        "comparison_id": "comparison-alpha",
    })
    store_json(tmp_path, "comparisons/comparison-beta/comparison.json", {
        "client_id": "beta",
        "comparison_id": "comparison-beta",
    })
    store_json(tmp_path, "trends/trend-alpha/trend.json", {
        "client_id": "alpha",
        "trend_id": "trend-alpha",
    })
    store_json(tmp_path, "trends/trend-beta/trend.json", {
        "client_id": "beta",
        "trend_id": "trend-beta",
    })
    store_json(tmp_path, "interpretations/session-alpha/session.json", {
        "session_id": "session-alpha",
        "source_type": "snapshot",
        "source_id": "snapshot-alpha",
    })
    store_json(tmp_path, "interpretations/session-beta/session.json", {
        "session_id": "session-beta",
        "source_type": "snapshot",
        "source_id": "snapshot-beta",
    })

    catalogue = catalogue_for(tmp_path, monkeypatch)

    assert [
        item["comparison_id"]
        for item in catalogue.list_comparisons("alpha")
    ] == ["comparison-alpha"]
    assert [item["trend_id"] for item in catalogue.list_trends("alpha")] == [
        "trend-alpha"
    ]
    assert catalogue.list_interpretations("alpha") == [{
        "session_id": "session-alpha",
        "source_type": "snapshot",
        "source_id": "snapshot-alpha",
        "client_id": "alpha",
    }]


def test_snapshot_bundle_rejects_another_clients_snapshot(tmp_path, monkeypatch):
    store_json(tmp_path, "snapshots/one/snapshot.json", {
        "client_id": "alpha",
        "snapshot_id": "one",
    })

    try:
        catalogue_for(tmp_path, monkeypatch).snapshot_bundle("one", "beta")
    except ValueError as error:
        assert "does not belong to client beta" in str(error)
    else:
        raise AssertionError("Expected cross-client snapshot access to be rejected")


def test_client_id_validation_matches_dataplatform_contract():
    assert validate_client_id("client_001") == "client_001"

    for invalid in ("Client-001", "client 001", "-client", ""):
        try:
            validate_client_id(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Expected invalid client ID to be rejected: {invalid}")


def test_read_table_follows_governed_artifact_reference(tmp_path, monkeypatch):
    store_text(
        tmp_path,
        "curated",
        "snapshots/one/data/evidence.csv",
        "ProjectID,Count\nP1,3\n",
    )

    frame = catalogue_for(tmp_path, monkeypatch).read_table(
        "curated/snapshots/one/data/evidence.csv"
    )

    assert frame.to_dict("records") == [{"ProjectID": "P1", "Count": 3}]


def test_read_snapshot_dataset_resolves_processed_manifest_reference(
    tmp_path, monkeypatch
):
    store_text(
        tmp_path,
        "processed",
        "history/one/tasks.csv",
        "TaskID,ProjectID\nT1,P1\n",
    )

    frame = catalogue_for(tmp_path, monkeypatch).read_snapshot_dataset(
        {"datasets": {"tasks": "history/one/tasks.csv"}},
        "tasks",
    )

    assert frame.to_dict("records") == [{"TaskID": "T1", "ProjectID": "P1"}]


def test_catalogue_rejects_artifact_path_traversal(tmp_path, monkeypatch):
    catalogue = catalogue_for(tmp_path, monkeypatch)

    try:
        catalogue.read_artifact("curated/../../outside.csv")
    except ValueError as error:
        assert "escapes governed storage" in str(error)
    else:
        raise AssertionError("Expected path traversal to be rejected")


def test_view_frames_keep_findings_and_fitness_distinct():
    fitness = flatten_fitness({"capabilities": {"schedule": {
        "status": "fit_with_caveats",
        "blocking_conditions": [],
        "caveats": [{}],
        "unavailable_rules": [],
    }}})
    findings = findings_frame({"findings": [{
        "finding_id": "SCH-1",
        "domain": "schedule",
        "severity": "high",
        "title": "Condition",
        "rule_id": "RULE-1",
        "affected_entities": {"projects": ["P1", "P2"]},
    }]})

    assert fitness.iloc[0]["Assessment"] == "Fit With Caveats"
    assert findings.iloc[0]["Affected entities"] == 2
