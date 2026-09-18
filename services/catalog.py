"""Read governed DataPlatform products without importing the platform package."""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any

import pandas as pd

from config.settings import Settings
from services.platform_reader import MetadataReadError


def _ids_from_keys(keys: list[str], collection: str, artifact: str) -> list[str]:
    prefix = f"{collection}/"
    suffix = f"/{artifact}"
    return sorted({
        key[len(prefix):-len(suffix)]
        for key in keys
        if key.startswith(prefix)
        and key.endswith(suffix)
        and "/" not in key[len(prefix):-len(suffix)]
    })


class Catalogue:
    """Small read-only facade over DataPlatform's local governed storage."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def _area_root(self, area: str) -> Path:
        if area not in {"raw", "processed", "curated", "metadata"}:
            raise ValueError(f"Unsupported storage area: {area}")
        return self.settings.data_path(area)

    def _path(self, area: str, key: str) -> Path:
        root = self._area_root(area).resolve()
        candidate = (root / Path(key)).resolve()
        if candidate != root and root not in candidate.parents:
            raise ValueError(f"Artifact reference escapes governed storage: {area}/{key}")
        return candidate

    def _read_json(self, area: str, key: str) -> dict[str, Any]:
        path = self._path(area, key)
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise MetadataReadError(
                f"Metadata file could not be read: {path} ({error})"
            ) from error
        if not isinstance(value, dict):
            raise MetadataReadError(f"Expected a JSON object in: {path}")
        return value

    def _list_files(self, area: str, prefix: str = "") -> list[str]:
        root = self._area_root(area).resolve()
        search_path = self._path(area, prefix) if prefix else root
        if not search_path.exists():
            return []
        if search_path.is_file():
            return [search_path.relative_to(root).as_posix()]
        return sorted(
            path.relative_to(root).as_posix()
            for path in search_path.rglob("*")
            if path.is_file()
        )

    def list_runs(self) -> list[dict[str, Any]]:
        keys = self._list_files("metadata", prefix="runs")
        run_ids = _ids_from_keys(keys, "runs", "run_summary.json")
        return [
            self._read_json("metadata", f"runs/{run_id}/run_summary.json")
            for run_id in reversed(run_ids)
        ]

    def list_snapshots(self) -> list[dict[str, Any]]:
        keys = self._list_files("metadata", prefix="snapshots")
        snapshots = [
            self._read_json("metadata", f"snapshots/{snapshot_id}/snapshot.json")
            for snapshot_id in _ids_from_keys(keys, "snapshots", "snapshot.json")
        ]
        return sorted(
            snapshots,
            key=lambda item: (
                str(item.get("observation_date") or ""),
                str(item.get("snapshot_id") or ""),
            ),
            reverse=True,
        )

    def snapshot_bundle(self, snapshot_id: str) -> dict[str, dict[str, Any]]:
        base = f"snapshots/{snapshot_id}"
        bundle = {
            "snapshot": self._read_json("metadata", f"{base}/snapshot.json")
        }
        for name in ("fitness", "diagnosis", "findings"):
            try:
                bundle[name] = self._read_json(
                    "metadata", f"{base}/{name}.json"
                )
            except FileNotFoundError:
                bundle[name] = {}
        return bundle

    def list_products(self, collection: str, artifact: str) -> list[dict[str, Any]]:
        keys = self._list_files("metadata", prefix=collection)
        return [
            self._read_json("metadata", f"{collection}/{item_id}/{artifact}")
            for item_id in reversed(_ids_from_keys(keys, collection, artifact))
        ]

    def list_comparisons(self) -> list[dict[str, Any]]:
        return self.list_products("comparisons", "comparison.json")

    def list_trends(self) -> list[dict[str, Any]]:
        return self.list_products("trends", "trend.json")

    def list_interpretations(self) -> list[dict[str, Any]]:
        return self.list_products("interpretations", "session.json")

    def read_artifact(self, reference: str) -> str:
        path = PurePosixPath(reference)
        if len(path.parts) < 2:
            raise ValueError(f"Unsupported artifact reference: {reference}")
        area = path.parts[0]
        key = "/".join(path.parts[1:])
        try:
            return self._path(area, key).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise MetadataReadError(
                f"Artifact could not be read: {reference} ({error})"
            ) from error

    def read_table(self, reference: str) -> pd.DataFrame:
        path = PurePosixPath(reference)
        if len(path.parts) < 2:
            raise ValueError(f"Unsupported artifact reference: {reference}")
        try:
            return pd.read_csv(self._path(path.parts[0], "/".join(path.parts[1:])))
        except (OSError, UnicodeError, pd.errors.ParserError) as error:
            raise MetadataReadError(
                f"Tabular artifact could not be read: {reference} ({error})"
            ) from error


def flatten_fitness(fitness: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for capability, assessment in fitness.get("capabilities", {}).items():
        rows.append({
            "Capability": capability.replace("_", " ").title(),
            "Assessment": assessment.get("status", "unknown").replace("_", " ").title(),
            "Blockers": len(assessment.get("blocking_conditions", [])),
            "Caveats": len(assessment.get("caveats", [])),
            "Unavailable rules": len(assessment.get("unavailable_rules", [])),
        })
    return pd.DataFrame(rows)


def findings_frame(findings_document: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for finding in findings_document.get("findings", []):
        entities = finding.get("affected_entities", {})
        rows.append({
            "Finding ID": finding.get("finding_id"),
            "Domain": finding.get("domain", "unknown").title(),
            "Severity": finding.get("severity", "unknown").title(),
            "Title": finding.get("title", "Untitled finding"),
            "Affected entities": sum(len(values) for values in entities.values()),
            "Rule": finding.get("rule_id"),
        })
    return pd.DataFrame(rows)
