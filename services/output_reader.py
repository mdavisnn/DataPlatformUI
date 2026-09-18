from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from config.settings import Settings
from services.platform_reader import MetadataReadError, optional_json


class OutputReadError(RuntimeError):
    pass


@dataclass(frozen=True)
class TabularOutput:
    name: str
    title: str
    group: str
    path: Path | None
    data: pd.DataFrame | None
    description: str = ""

    @property
    def available(self) -> bool:
        return self.path is not None and self.data is not None


ANALYSIS_OUTPUTS = (
    ("Point-in-time", "project_schedule_health.csv", "Project schedule health"),
    ("Point-in-time", "resource_conflicts.csv", "Resource conflicts"),
    ("Point-in-time", "ppm_exceptions.csv", "PPM exceptions"),
    ("Point-in-time", "ppm_exceptions_summary.csv", "PPM exception summary"),
    ("History", "project_changes.csv", "Project changes"),
    ("History", "project_status_history.csv", "Project status history"),
    ("History", "project_schedule_stability.csv", "Project schedule stability"),
    ("Data quality", "data_quality_summary.csv", "Data quality summary"),
)


def _safe_run_path(settings: Settings, run_id: str) -> Path:
    if not run_id or Path(run_id).name != run_id:
        raise OutputReadError("Invalid run ID.")
    return settings.runs_path / run_id


def _read_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except (OSError, UnicodeError, pd.errors.ParserError) as exc:
        raise OutputReadError(f"Output file could not be read: {path} ({exc})") from exc


def _resolve_under(root: Path, object_key: str) -> Path | None:
    candidate = (root / object_key).resolve()
    resolved_root = root.resolve()
    if candidate != resolved_root and resolved_root not in candidate.parents:
        return None
    return candidate if candidate.is_file() else None


def load_processing(settings: Settings, run_id: str) -> dict[str, Any]:
    return optional_json(_safe_run_path(settings, run_id) / "processing.json") or {}


def load_profiles(settings: Settings, run_id: str) -> dict[str, dict[str, Any]]:
    profiles_dir = _safe_run_path(settings, run_id) / "profiles"
    if not profiles_dir.is_dir():
        return {}
    profiles: dict[str, dict[str, Any]] = {}
    for path in sorted(profiles_dir.glob("*.json")):
        try:
            payload = optional_json(path)
        except MetadataReadError:
            continue
        if payload:
            profiles[path.stem] = payload
    return profiles


def load_validation_errors(settings: Settings, run_id: str) -> TabularOutput | None:
    path = _safe_run_path(settings, run_id) / "validation_errors.csv"
    if not path.is_file():
        return None
    return TabularOutput(path.name, "Validation errors", "Validation", path, _read_csv(path))


def load_processed_outputs(settings: Settings, run_id: str) -> list[TabularOutput]:
    processing = load_processing(settings, run_id)
    outputs: list[TabularOutput] = []
    for item in processing.get("datasets", []):
        if not isinstance(item, dict):
            continue
        dataset = str(item.get("dataset") or "dataset")
        key = item.get("history_key") or item.get("output_key")
        path = _resolve_under(settings.processed_path, str(key)) if key else None
        outputs.append(TabularOutput(
            name=Path(str(key)).name if key else f"{dataset}.csv",
            title=dataset.replace("_", " ").title(), group="Processed",
            path=path, data=_read_csv(path) if path else None,
            description=f"{item.get('rows_out', 'Unknown')} rows written",
        ))
    return outputs


def load_curation_outputs(settings: Settings, run_id: str) -> list[TabularOutput]:
    curation_dir = _safe_run_path(settings, run_id) / "curation"
    if not curation_dir.is_dir():
        return []
    outputs: list[TabularOutput] = []
    for metadata_path in sorted(curation_dir.glob("*.json")):
        try:
            metadata = optional_json(metadata_path) or {}
        except MetadataReadError:
            continue
        key = metadata.get("curated_object") or metadata.get("current_object")
        path = _resolve_under(settings.curated_path, str(key)) if key else None
        outputs.append(TabularOutput(
            name=Path(str(key)).name if key else f"{metadata_path.stem}.csv",
            title=metadata_path.stem.replace("_", " ").title(), group="Curation",
            path=path, data=_read_csv(path) if path else None,
            description=f"{metadata.get('rows_written', 'Unknown')} rows · quality {metadata.get('validation_quality_status', 'unknown')}",
        ))
    return outputs


def load_analysis_outputs(settings: Settings) -> list[TabularOutput]:
    outputs: list[TabularOutput] = []
    known_names = {name for _, name, _ in ANALYSIS_OUTPUTS}
    for group, name, title in ANALYSIS_OUTPUTS:
        path = _resolve_under(settings.curated_path, name)
        outputs.append(TabularOutput(name, title, group, path, _read_csv(path) if path else None))
    if settings.curated_path.is_dir():
        for path in sorted(settings.curated_path.glob("*.csv")):
            if path.name in known_names or path.name in {"portfolio_summary.csv", "resource_utilisation.csv"}:
                continue
            outputs.append(TabularOutput(path.name, path.stem.replace("_", " ").title(), "Other current outputs", path, _read_csv(path)))
    return outputs


def load_snapshots(settings: Settings, run_id: str) -> dict[str, dict[str, Any]]:
    _safe_run_path(settings, run_id)
    if not settings.snapshots_path.is_dir():
        return {}
    snapshots: dict[str, dict[str, Any]] = {}
    for dataset_dir in sorted(settings.snapshots_path.iterdir()):
        path = dataset_dir / f"{run_id}.json"
        try:
            payload = optional_json(path)
        except MetadataReadError:
            continue
        if dataset_dir.is_dir() and payload:
            snapshots[dataset_dir.name] = payload
    return snapshots
