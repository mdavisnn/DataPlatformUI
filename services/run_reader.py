from __future__ import annotations

from pathlib import Path

from config.settings import Settings
from models.run import PipelineRun
from services.platform_reader import MetadataReadError, read_json


class RunReadError(RuntimeError):
    pass


def _normalise_run(run_id: str, data: dict) -> PipelineRun:
    stages_raw = data.get("stages") or data.get("stage_statuses") or {}
    if isinstance(stages_raw, list):
        stages = {str(item.get("stage")): str(item.get("status", "unknown")) for item in stages_raw if isinstance(item, dict)}
    elif isinstance(stages_raw, dict):
        stages = {
            str(name): str(value.get("status", "unknown") if isinstance(value, dict) else value)
            for name, value in stages_raw.items()
        }
    else:
        stages = {}
    return PipelineRun(
        run_id=str(data.get("run_id") or run_id),
        status=str(data.get("status") or data.get("final_status") or "unknown").lower(),
        started_at=data.get("started_at") or data.get("created_at"),
        completed_at=data.get("completed_at") or data.get("ended_at"),
        failed_stage=data.get("failed_stage"),
        engagement_name=data.get("engagement_name") or data.get("dataset_name"),
        stages=stages,
        source_file_count=data.get("source_file_count") or data.get("file_count"),
        record_count=data.get("record_count") or data.get("total_records"),
    )


def list_runs(settings: Settings) -> list[PipelineRun]:
    root = settings.runs_path
    if not root.is_dir():
        return []
    runs: list[PipelineRun] = []
    for run_dir in root.iterdir():
        if not run_dir.is_dir() or not (run_dir / "run.json").is_file():
            continue
        try:
            runs.append(_normalise_run(run_dir.name, read_json(run_dir / "run.json")))
        except MetadataReadError:
            continue
    return sorted(runs, key=lambda run: (run.sort_time, run.run_id), reverse=True)


def load_run(settings: Settings, run_id: str) -> PipelineRun:
    if not run_id or Path(run_id).name != run_id:
        raise RunReadError("Invalid run ID.")
    try:
        return _normalise_run(run_id, read_json(settings.runs_path / run_id / "run.json"))
    except MetadataReadError as exc:
        raise RunReadError(str(exc)) from exc


def get_stage_statuses(settings: Settings, run_id: str) -> dict[str, str]:
    return load_run(settings, run_id).stages

