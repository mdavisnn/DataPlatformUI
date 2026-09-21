from datetime import date
from subprocess import CompletedProcess
from unittest.mock import patch

import pytest

from config.settings import Settings
from services.workflow import (
    assess_evidence,
    diagnose_snapshot,
    inspect_evidence,
)


def test_inspection_passes_the_selected_client_to_dataplatform(tmp_path):
    settings = Settings(tmp_path)

    with patch(
        "services.workflow.subprocess.run",
        return_value=CompletedProcess([], 0, "inspection complete", ""),
    ) as run:
        result = inspect_evidence(settings, "client-001")

    assert result == {"exit_code": 0, "output": "inspection complete"}
    command = run.call_args.args[0]
    assert command[-4:] == [
        "-m",
        "lab.inspect",
        "--client-id",
        "client-001",
    ]
    assert run.call_args.kwargs["cwd"] == tmp_path
    assert run.call_args.kwargs["env"]["DATA_PLATFORM_STORAGE_ROOT"] == str(
        tmp_path / "local-data"
    )


def test_inspection_can_use_a_fixed_run_id(tmp_path):
    settings = Settings(tmp_path)

    with patch(
        "services.workflow.subprocess.run",
        return_value=CompletedProcess([], 0, "inspection complete", ""),
    ) as run:
        inspect_evidence(settings, "demo-ui", "demo-run-001")

    assert run.call_args.args[0][-6:] == [
        "-m",
        "lab.inspect",
        "--client-id",
        "demo-ui",
        "--run-id",
        "demo-run-001",
    ]


def test_assessment_passes_client_run_and_observation_date(tmp_path):
    settings = Settings(tmp_path)

    with patch(
        "services.workflow.subprocess.run",
        return_value=CompletedProcess([], 0, "assessment complete", ""),
    ) as run:
        result = assess_evidence(
            settings,
            "client-001",
            "run-001",
            date(2026, 9, 30),
        )

    assert result["exit_code"] == 0
    assert run.call_args.args[0][-6:] == [
        "--client-id", "client-001",
        "--run-id", "run-001",
        "--observation-date", "2026-09-30",
    ]


def test_diagnosis_passes_client_snapshot_and_overrides(tmp_path):
    settings = Settings(tmp_path)

    with patch(
        "services.workflow.subprocess.run",
        return_value=CompletedProcess([], 0, "diagnosis complete", ""),
    ) as run:
        result = diagnose_snapshot(
            settings,
            "client-001",
            "snapshot-001",
            ["resource"],
        )

    assert result["exit_code"] == 0
    assert run.call_args.args[0][-6:] == [
        "--client-id", "client-001",
        "--snapshot-id", "snapshot-001",
        "--allow-not-fit", "resource",
    ]


def test_invalid_client_state_never_launches_an_operation(tmp_path):
    settings = Settings(tmp_path)

    with patch("services.workflow.subprocess.run") as run:
        with pytest.raises(ValueError, match="Client ID must"):
            assess_evidence(
                settings,
                "Another Client",
                "run-001",
                date(2026, 9, 30),
            )

    run.assert_not_called()
