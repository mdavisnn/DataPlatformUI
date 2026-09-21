import json
from unittest.mock import patch

from config.settings import Settings
from services.demo import (
    CLIENT_ID,
    DATASET_FILENAMES,
    OBSERVATION_DATE,
    RUN_ID,
    SNAPSHOT_ID,
    main,
)


def successful_result():
    return {"exit_code": 0, "output": "complete"}


def test_demo_stages_v2_sources_and_runs_the_governed_workflow(tmp_path):
    settings = Settings(tmp_path)

    with (
        patch("services.demo.inspect_evidence", return_value=successful_result()) as inspect,
        patch("services.demo.assess_evidence", return_value=successful_result()) as assess,
        patch("services.demo.diagnose_snapshot", return_value=successful_result()) as diagnose,
    ):
        result = main(settings)

    assert result == 0
    staged = settings.storage_root / "staged" / CLIENT_ID
    assert {path.name for path in staged.iterdir()} == set(DATASET_FILENAMES)
    inspect.assert_called_once_with(settings, CLIENT_ID, RUN_ID)
    assess.assert_called_once_with(
        settings,
        CLIENT_ID,
        RUN_ID,
        OBSERVATION_DATE,
    )
    diagnose.assert_called_once_with(settings, CLIENT_ID, SNAPSHOT_ID)


def test_demo_does_not_overwrite_changed_staged_evidence(tmp_path):
    settings = Settings(tmp_path)
    staged = settings.storage_root / "staged" / CLIENT_ID
    staged.mkdir(parents=True)
    changed = staged / "projects.csv"
    changed.write_text("client-owned content", encoding="utf-8")

    with patch("services.demo.inspect_evidence") as inspect:
        result = main(settings)

    assert result == 1
    assert changed.read_text(encoding="utf-8") == "client-owned content"
    inspect.assert_not_called()


def test_demo_does_not_mix_with_other_staged_files(tmp_path):
    settings = Settings(tmp_path)
    staged = settings.storage_root / "staged" / CLIENT_ID
    staged.mkdir(parents=True)
    (staged / "other.csv").write_text("OtherID\n1\n", encoding="utf-8")

    with patch("services.demo.inspect_evidence") as inspect:
        result = main(settings)

    assert result == 1
    inspect.assert_not_called()


def test_demo_reuses_an_existing_diagnosed_observation(tmp_path):
    settings = Settings(tmp_path)
    snapshot = settings.storage_root / "metadata" / "snapshots" / SNAPSHOT_ID
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
