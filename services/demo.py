"""Create a synthetic v2 observation through DataPlatform's real workflow."""

from __future__ import annotations

import json
import shutil
from datetime import date
from pathlib import Path

from config.settings import Settings
from services.workflow import (
    assess_evidence,
    diagnose_snapshot,
    inspect_evidence,
)


CLIENT_ID = "demo-ui"
RUN_ID = "demo-ui-20260831-00000001"
OBSERVATION_DATE = date(2026, 8, 31)
SNAPSHOT_ID = f"{OBSERVATION_DATE}-{RUN_ID[-8:]}"
DATASET_FILENAMES = (
    "projects.csv",
    "tasks.csv",
    "resources.csv",
    "assignments.csv",
    "dependencies.csv",
)
SOURCE_DIRECTORY = Path(__file__).resolve().parents[1] / "demo_data" / "v2"


class DemoError(RuntimeError):
    """Raised when the synthetic demo cannot be created safely."""


def _load_json(path: Path) -> dict:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DemoError(
            f"Could not read existing demo state at {path}: {error}"
        ) from error
    if not isinstance(document, dict):
        raise DemoError(f"Existing demo state is not a JSON object: {path}")
    return document


def _require_demo_identity(document: dict, path: Path) -> None:
    if document.get("client_id") != CLIENT_ID:
        raise DemoError(
            f"Refusing to reuse {path}: it does not belong to {CLIENT_ID}."
        )


def _stage_sources(settings: Settings) -> Path:
    """Copy packaged demo evidence into the raw client inbox safely."""

    missing = [
        filename
        for filename in DATASET_FILENAMES
        if not (SOURCE_DIRECTORY / filename).is_file()
    ]
    if missing:
        raise DemoError(
            "The packaged v2 demo is incomplete: " + ", ".join(missing)
        )

    staging_root = (settings.storage_root / "raw" / CLIENT_ID).resolve()
    storage_root = settings.storage_root.resolve()
    if storage_root not in staging_root.parents:
        raise DemoError("The demo staging path escapes governed storage.")

    expected = set(DATASET_FILENAMES)
    unexpected = []
    if staging_root.is_dir():
        unexpected = sorted(
            path.relative_to(staging_root).as_posix()
            for path in staging_root.rglob("*")
            if path.is_file()
            and path.relative_to(staging_root).as_posix() not in expected
        )
    if unexpected:
        raise DemoError(
            "Refusing to mix packaged demo evidence with other raw files: "
            + ", ".join(unexpected)
        )

    conflicts = []
    for filename in DATASET_FILENAMES:
        source = SOURCE_DIRECTORY / filename
        target = staging_root / filename
        if target.exists() and target.read_bytes() != source.read_bytes():
            conflicts.append(filename)
    if conflicts:
        raise DemoError(
            "Refusing to overwrite changed raw demo evidence: "
            + ", ".join(conflicts)
            + ". Remove or rename raw/demo-ui before retrying."
        )

    staging_root.mkdir(parents=True, exist_ok=True)
    for filename in DATASET_FILENAMES:
        source = SOURCE_DIRECTORY / filename
        target = staging_root / filename
        if not target.exists():
            shutil.copyfile(source, target)
    return staging_root


def _run_step(label: str, operation) -> bool:
    result = operation()
    print(f"\n--- {label} ---")
    if result.get("output"):
        print(result["output"])
    if result.get("exit_code") != 0:
        print(f"[FAIL] {label} failed with exit code {result.get('exit_code')}.")
        return False
    return True


def _existing_state(settings: Settings) -> str:
    """Return the next workflow phase while validating fixed demo identity."""

    metadata = settings.storage_root / "metadata"
    client_root = metadata / CLIENT_ID
    snapshot_path = (
        client_root / "snapshots" / SNAPSHOT_ID / "snapshot.json"
    )
    diagnosis_path = (
        client_root / "snapshots" / SNAPSHOT_ID / "diagnosis.json"
    )
    run_path = client_root / "runs" / RUN_ID / "run.json"

    if snapshot_path.is_file():
        snapshot = _load_json(snapshot_path)
        _require_demo_identity(snapshot, snapshot_path)
        if snapshot.get("run_id") != RUN_ID:
            raise DemoError(
                f"Refusing to reuse {snapshot_path}: run_id does not match {RUN_ID}."
            )
        if diagnosis_path.is_file():
            diagnosis = _load_json(diagnosis_path)
            _require_demo_identity(diagnosis, diagnosis_path)
            return "complete"
        return "diagnose"

    if run_path.is_file():
        run = _load_json(run_path)
        _require_demo_identity(run, run_path)
        if run.get("snapshot_id"):
            raise DemoError(
                f"Run {RUN_ID} references a snapshot whose manifest is missing."
            )
        if run.get("profile_status") == "success":
            return "assess"
        raise DemoError(
            f"Run {RUN_ID} exists but inspection is not complete; review {run_path}."
        )

    return "inspect"


def main(settings: Settings | None = None) -> int:
    settings = settings or Settings.from_environment()
    try:
        staging_root = _stage_sources(settings)
        phase = _existing_state(settings)
    except (DemoError, OSError) as error:
        print(f"[FAIL] {error}")
        return 1

    print("=" * 60)
    print("CREATE DATAPLATFORM V2 DEMO")
    print("=" * 60)
    print(f"Client ID:        {CLIENT_ID}")
    print(f"Observation date: {OBSERVATION_DATE}")
    print(f"Staged evidence:  {staging_root}")

    if phase == "complete":
        print(f"Demo observation already exists: {SNAPSHOT_ID}")
        return 0

    if phase == "inspect" and not _run_step(
        "Inspect evidence",
        lambda: inspect_evidence(settings, CLIENT_ID, RUN_ID),
    ):
        return 1

    if phase in {"inspect", "assess"} and not _run_step(
        "Assess evidence",
        lambda: assess_evidence(
            settings,
            CLIENT_ID,
            RUN_ID,
            OBSERVATION_DATE,
        ),
    ):
        return 1

    if not _run_step(
        "Diagnose observation",
        lambda: diagnose_snapshot(settings, CLIENT_ID, SNAPSHOT_ID),
    ):
        return 1

    print(f"\nDataPlatform v2 demo created: {SNAPSHOT_ID}")
    print("Select client demo-ui in the console to review it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
