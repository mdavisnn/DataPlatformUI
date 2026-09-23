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


def register_client(root, client_id):
    store_json(
        root,
        f"{client_id}/client.json",
        {"format_version": "1.0", "client_id": client_id},
    )


def catalogue_for(tmp_path, monkeypatch):
    monkeypatch.delenv("DATA_PLATFORM_STORAGE_ROOT", raising=False)
    return Catalogue(Settings(tmp_path))


def test_catalogue_lists_client_owned_snapshots_by_observation_date(
    tmp_path, monkeypatch,
):
    register_client(tmp_path, "client-001")
    store_json(tmp_path, "client-001/snapshots/older/snapshot.json", {
        "client_id": "client-001",
        "snapshot_id": "older",
        "observation_date": "2026-01-31",
    })
    store_json(tmp_path, "client-001/snapshots/newer/snapshot.json", {
        "client_id": "client-001",
        "snapshot_id": "newer",
        "observation_date": "2026-02-28",
    })

    snapshots = catalogue_for(tmp_path, monkeypatch).list_snapshots(
        "client-001"
    )

    assert [item["snapshot_id"] for item in snapshots] == [
        "newer", "older"
    ]


def test_snapshot_bundle_tolerates_optional_products(
    tmp_path, monkeypatch,
):
    register_client(tmp_path, "client-001")
    store_json(tmp_path, "client-001/snapshots/one/snapshot.json", {
        "client_id": "client-001",
        "snapshot_id": "one",
    })

    assert catalogue_for(tmp_path, monkeypatch).snapshot_bundle(
        "one", "client-001"
    ) == {
        "snapshot": {
            "client_id": "client-001", "snapshot_id": "one"
        },
        "fitness": {},
        "diagnosis": {},
        "findings": {},
    }


def test_catalogue_lists_clients_and_scopes_products(
    tmp_path, monkeypatch,
):
    for client_id in ("alpha", "beta"):
        register_client(tmp_path, client_id)
        store_json(
            tmp_path,
            f"{client_id}/runs/run-{client_id}/run.json",
            {"client_id": client_id, "run_id": f"run-{client_id}"},
        )
        store_json(
            tmp_path,
            f"{client_id}/snapshots/snapshot-{client_id}/snapshot.json",
            {
                "client_id": client_id,
                "snapshot_id": f"snapshot-{client_id}",
                "observation_date": "2026-08-31",
            },
        )

    catalogue = catalogue_for(tmp_path, monkeypatch)

    assert catalogue.list_clients() == ["alpha", "beta"]
    assert [item["run_id"] for item in catalogue.list_runs("alpha")] == [
        "run-alpha"
    ]
    assert [
        item["snapshot_id"] for item in catalogue.list_snapshots("beta")
    ] == ["snapshot-beta"]


def test_catalogue_includes_valid_raw_inbox_clients(
    tmp_path, monkeypatch,
):
    (tmp_path / "local-data" / "raw" / "new-client").mkdir(
        parents=True
    )
    (tmp_path / "local-data" / "raw" / "Invalid Client").mkdir()

    assert catalogue_for(tmp_path, monkeypatch).list_clients() == [
        "new-client"
    ]


def test_catalogue_scopes_history_and_interpretations(
    tmp_path, monkeypatch,
):
    for client_id in ("alpha", "beta"):
        register_client(tmp_path, client_id)
        store_json(
            tmp_path,
            f"{client_id}/comparisons/comparison-{client_id}/comparison.json",
            {
                "client_id": client_id,
                "comparison_id": f"comparison-{client_id}",
            },
        )
        store_json(
            tmp_path,
            f"{client_id}/trends/trend-{client_id}/trend.json",
            {
                "client_id": client_id,
                "trend_id": f"trend-{client_id}",
            },
        )
        store_json(
            tmp_path,
            f"{client_id}/interpretations/session-{client_id}/session.json",
            {
                "client_id": client_id,
                "interpretation_id": f"session-{client_id}",
            },
        )

    catalogue = catalogue_for(tmp_path, monkeypatch)

    assert [
        item["comparison_id"]
        for item in catalogue.list_comparisons("alpha")
    ] == ["comparison-alpha"]
    assert [item["trend_id"] for item in catalogue.list_trends("alpha")] == [
        "trend-alpha"
    ]
    assert catalogue.list_interpretations("alpha") == [{
        "client_id": "alpha",
        "interpretation_id": "session-alpha",
    }]


def test_snapshot_bundle_rejects_another_clients_snapshot(
    tmp_path, monkeypatch,
):
    register_client(tmp_path, "alpha")
    store_json(tmp_path, "alpha/snapshots/one/snapshot.json", {
        "client_id": "alpha",
        "snapshot_id": "one",
    })

    try:
        catalogue_for(tmp_path, monkeypatch).snapshot_bundle("one", "beta")
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("Expected cross-client access to be rejected")


def test_client_id_validation_matches_dataplatform_contract():
    assert validate_client_id("client_001") == "client_001"
    for invalid in ("Client-001", "client 001", "-client", ""):
        try:
            validate_client_id(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(
                f"Expected invalid client ID to be rejected: {invalid}"
            )


def test_read_table_follows_governed_artifact_reference(
    tmp_path, monkeypatch,
):
    store_text(
        tmp_path,
        "curated",
        "client-001/snapshots/one/data/evidence.csv",
        "ProjectID,Count\nP1,3\n",
    )
    frame = catalogue_for(tmp_path, monkeypatch).read_table(
        "curated/client-001/snapshots/one/data/evidence.csv"
    )
    assert frame.to_dict("records") == [{"ProjectID": "P1", "Count": 3}]


def test_read_snapshot_dataset_resolves_manifest_reference(
    tmp_path, monkeypatch,
):
    store_text(
        tmp_path,
        "processed",
        "client-001/snapshots/one/tasks.csv",
        "TaskID,ProjectID\nT1,P1\n",
    )
    frame = catalogue_for(tmp_path, monkeypatch).read_snapshot_dataset(
        {
            "datasets": {
                "tasks": "client-001/snapshots/one/tasks.csv"
            }
        },
        "tasks",
    )
    assert frame.to_dict("records") == [
        {"TaskID": "T1", "ProjectID": "P1"}
    ]


def test_catalogue_rejects_artifact_path_traversal(
    tmp_path, monkeypatch,
):
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
