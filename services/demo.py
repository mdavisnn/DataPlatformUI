"""Create a synthetic v2 observation through DataPlatform's real workflow."""

from __future__ import annotations

import argparse
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
SYNTHETIC_CLIENT_IDS = (CLIENT_ID, "demo-001")
_STORAGE_AREAS = ("raw", "processed", "curated", "metadata")


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


def _require_reset_target(target: Path, parent: Path) -> None:
    resolved_parent = parent.resolve()
    resolved_target = target.resolve()
    if (
        resolved_target == resolved_parent
        or resolved_parent not in resolved_target.parents
    ):
        raise DemoError(
            f"Refusing to reset a path outside its synthetic root: {target}"
        )


def _validate_scenario_demo_root(root: Path, client_id: str) -> None:
    if not root.is_dir():
        return
    configurations = list(root.glob("runs/*/configuration.json"))
    run_directories = list((root / "runs").glob("*"))
    if run_directories and len(configurations) != len(run_directories):
        raise DemoError(
            f"Refusing to reset incomplete scenario demo state at {root}."
        )
    for configuration_path in configurations:
        configuration = _load_json(configuration_path)
        configured_client = configuration.get("input", {}).get("client_id")
        if configured_client != client_id:
            raise DemoError(
                f"Refusing to reset {root}: {configuration_path} belongs "
                f"to {configured_client or 'an unknown client'}."
            )


def reset_synthetic_demo(settings: Settings) -> tuple[Path, ...]:
    """Remove only the fixed current and legacy synthetic demo identities."""

    targets: list[tuple[Path, Path]] = []
    for area in _STORAGE_AREAS:
        area_root = settings.storage_root / area
        for client_id in SYNTHETIC_CLIENT_IDS:
            target = area_root / client_id
            _require_reset_target(target, area_root)
            targets.append((target, area_root))

    output_root = settings.schedule_output_root
    for client_id in SYNTHETIC_CLIENT_IDS:
        target = output_root / client_id
        _require_reset_target(target, output_root)
        _validate_scenario_demo_root(target, client_id)
        targets.append((target, output_root))

    for client_id in SYNTHETIC_CLIENT_IDS:
        identity_path = (
            settings.storage_root / "metadata" / client_id / "client.json"
        )
        if identity_path.is_file():
            identity = _load_json(identity_path)
            if identity.get("client_id") != client_id:
                raise DemoError(
                    f"Refusing to reset {identity_path}: its client identity "
                    "does not match its synthetic directory."
                )

    removed = []
    for target, _parent in targets:
        if target.is_dir():
            shutil.rmtree(target)
            removed.append(target.resolve())
    return tuple(removed)


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


def main(settings: Settings | None = None, *, reset: bool = False) -> int:
    settings = settings or Settings.from_environment()
    try:
        removed = reset_synthetic_demo(settings) if reset else ()
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
    if reset:
        print(f"Synthetic roots reset: {len(removed)}")

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
    parser = argparse.ArgumentParser(
        description="Create the fixed DataPlatformUI synthetic observation."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help=(
            "Remove only demo-ui and legacy demo-001 synthetic data and "
            "scenario runs before rebuilding demo-ui."
        ),
    )
    arguments = parser.parse_args()
    raise SystemExit(main(reset=arguments.reset))
