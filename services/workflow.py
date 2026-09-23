"""Launch DataPlatform's existing consultant commands from the local UI."""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import date

from config.settings import Settings
from services.catalog import validate_client_id


def _client_arguments(client_id: str) -> list[str]:
    """Build the client boundary required when inspection begins."""

    return ["--client-id", validate_client_id(client_id)]


def _run(settings: Settings, module: str, arguments: list[str] | None = None) -> dict:
    command = [sys.executable, "-m", module, *(arguments or [])]
    environment = os.environ.copy()
    environment["DATA_PLATFORM_STORAGE_ROOT"] = str(settings.storage_root)
    try:
        result = subprocess.run(
            command,
            cwd=settings.platform_path,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=900,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"exit_code": 1, "output": f"Could not run {' '.join(command)}: {error}"}
    output = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()
    return {"exit_code": result.returncode, "output": output}


def inspect_evidence(
    settings: Settings,
    client_id: str,
    run_id: str | None = None,
) -> dict:
    arguments = _client_arguments(client_id)
    if run_id:
        arguments.extend(["--run-id", run_id])
    return _run(
        settings,
        "lab.inspect",
        arguments,
    )


def assess_evidence(
    settings: Settings,
    client_id: str,
    run_id: str,
    observation_date: date,
) -> dict:
    validate_client_id(client_id)
    return _run(
        settings,
        "lab.assess",
        [
            "--run-id", run_id,
            "--observation-date", str(observation_date),
        ],
    )


def diagnose_snapshot(
    settings: Settings,
    client_id: str,
    snapshot_id: str,
    allow_not_fit: list[str] | None = None,
) -> dict:
    validate_client_id(client_id)
    arguments = [
        "--snapshot-id", snapshot_id,
    ]
    for capability in allow_not_fit or []:
        arguments.extend(["--allow-not-fit", capability])
    return _run(settings, "lab.diagnose", arguments)
