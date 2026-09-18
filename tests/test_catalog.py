import json

from config.settings import Settings
from services.catalog import Catalogue, findings_frame, flatten_fitness


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
        "snapshot_id": "older", "observation_date": "2026-01-31"
    })
    store_json(tmp_path, "snapshots/newer/snapshot.json", {
        "snapshot_id": "newer", "observation_date": "2026-02-28"
    })

    snapshots = catalogue_for(tmp_path, monkeypatch).list_snapshots()

    assert [item["snapshot_id"] for item in snapshots] == ["newer", "older"]


def test_snapshot_bundle_tolerates_optional_products(tmp_path, monkeypatch):
    store_json(tmp_path, "snapshots/one/snapshot.json", {"snapshot_id": "one"})

    assert catalogue_for(tmp_path, monkeypatch).snapshot_bundle("one") == {
        "snapshot": {"snapshot_id": "one"},
        "fitness": {},
        "diagnosis": {},
        "findings": {},
    }


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
