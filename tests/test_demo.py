import json
from unittest.mock import patch

from config.settings import Settings
from services.demo import (
    CLIENT_ID,
    DATASET_FILENAMES,
    OBSERVATION_DATE,
    RUN_ID,
    SNAPSHOT_ID,
    SYNTHETIC_CLIENT_IDS,
    main,
    reset_synthetic_demo,
)


def successful_result():
    return {"exit_code": 0, "output": "complete"}


def test_demo_copies_v2_sources_to_raw_and_runs_the_workflow(tmp_path):
    settings = Settings(tmp_path)

    with (
        patch("services.demo.inspect_evidence", return_value=successful_result()) as inspect,
        patch("services.demo.assess_evidence", return_value=successful_result()) as assess,
        patch("services.demo.diagnose_snapshot", return_value=successful_result()) as diagnose,
    ):
        result = main(settings)

    assert result == 0
    inbox = settings.storage_root / "raw" / CLIENT_ID
    assert {path.name for path in inbox.iterdir()} == set(DATASET_FILENAMES)
    inspect.assert_called_once_with(settings, CLIENT_ID, RUN_ID)
    assess.assert_called_once_with(
        settings,
        CLIENT_ID,
        RUN_ID,
        OBSERVATION_DATE,
    )
    diagnose.assert_called_once_with(settings, CLIENT_ID, SNAPSHOT_ID)


def test_demo_does_not_overwrite_changed_raw_evidence(tmp_path):
    settings = Settings(tmp_path)
    inbox = settings.storage_root / "raw" / CLIENT_ID
    inbox.mkdir(parents=True)
    changed = inbox / "projects.csv"
    changed.write_text("client-owned content", encoding="utf-8")

    with patch("services.demo.inspect_evidence") as inspect:
        result = main(settings)

    assert result == 1
    assert changed.read_text(encoding="utf-8") == "client-owned content"
    inspect.assert_not_called()


def test_demo_does_not_mix_with_other_raw_files(tmp_path):
    settings = Settings(tmp_path)
    inbox = settings.storage_root / "raw" / CLIENT_ID
    inbox.mkdir(parents=True)
    (inbox / "other.csv").write_text("OtherID\n1\n", encoding="utf-8")

    with patch("services.demo.inspect_evidence") as inspect:
        result = main(settings)

    assert result == 1
    inspect.assert_not_called()


def test_demo_reuses_an_existing_diagnosed_observation(tmp_path):
    settings = Settings(tmp_path)
    snapshot = (
        settings.storage_root / "metadata" / CLIENT_ID
        / "snapshots" / SNAPSHOT_ID
    )
    snapshot.mkdir(parents=True)
    (snapshot / "snapshot.json").write_text(
        json.dumps({"client_id": CLIENT_ID, "run_id": RUN_ID}),
        encoding="utf-8",
    )
    (snapshot / "diagnosis.json").write_text(
        json.dumps({"client_id": CLIENT_ID}),
        encoding="utf-8",
    )

    with (
        patch("services.demo.inspect_evidence") as inspect,
        patch("services.demo.assess_evidence") as assess,
        patch("services.demo.diagnose_snapshot") as diagnose,
    ):
        result = main(settings)

    assert result == 0
    inspect.assert_not_called()
    assess.assert_not_called()
    diagnose.assert_not_called()


def test_demo_stops_when_inspection_fails(tmp_path):
    settings = Settings(tmp_path)

    with (
        patch(
            "services.demo.inspect_evidence",
            return_value={"exit_code": 1, "output": "inspection failed"},
        ),
        patch("services.demo.assess_evidence") as assess,
        patch("services.demo.diagnose_snapshot") as diagnose,
    ):
        result = main(settings)

    assert result == 1
    assess.assert_not_called()
    diagnose.assert_not_called()


def test_demo_reset_removes_only_fixed_synthetic_clients(
    tmp_path, monkeypatch,
):
    platform = tmp_path / "DataPlatform"
    schedule = tmp_path / "SchedulePlatform"
    monkeypatch.setenv("SCHEDULE_PLATFORM_PATH", str(schedule))
    settings = Settings(platform)

    for client_id in SYNTHETIC_CLIENT_IDS:
        for area in ("raw", "processed", "curated", "metadata"):
            root = settings.storage_root / area / client_id
            root.mkdir(parents=True)
            (root / "synthetic.txt").write_text("demo", encoding="utf-8")
        (settings.storage_root / "metadata" / client_id / "client.json").write_text(
            json.dumps({"client_id": client_id}), encoding="utf-8"
        )
        run_root = settings.schedule_output_root / client_id / "runs" / "run-1"
        run_root.mkdir(parents=True)
        (run_root / "configuration.json").write_text(
            json.dumps({"input": {"client_id": client_id}}),
            encoding="utf-8",
        )

    protected = settings.storage_root / "metadata" / "client-001"
    protected.mkdir(parents=True)
    (protected / "client.json").write_text(
        json.dumps({"client_id": "client-001"}), encoding="utf-8"
    )

    removed = reset_synthetic_demo(settings)

    assert removed
    for client_id in SYNTHETIC_CLIENT_IDS:
        assert not (
            settings.storage_root / "metadata" / client_id
        ).exists()
        assert not (settings.schedule_output_root / client_id).exists()
    assert protected.is_dir()


def test_demo_reset_refuses_mismatched_scenario_identity(
    tmp_path, monkeypatch,
):
    platform = tmp_path / "DataPlatform"
    schedule = tmp_path / "SchedulePlatform"
    monkeypatch.setenv("SCHEDULE_PLATFORM_PATH", str(schedule))
    settings = Settings(platform)
    run_root = (
        settings.schedule_output_root / CLIENT_ID / "runs" / "unexpected"
    )
    run_root.mkdir(parents=True)
    (run_root / "configuration.json").write_text(
        json.dumps({"input": {"client_id": "client-001"}}),
        encoding="utf-8",
    )

    result = main(settings, reset=True)

    assert result == 1
    assert run_root.is_dir()
