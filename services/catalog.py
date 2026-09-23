"""Read client-owned DataPlatform products without importing the platform."""

from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

import pandas as pd
import streamlit as st

from config.settings import Settings
from services.platform_reader import MetadataReadError


CLIENT_ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")


@st.cache_data(ttl=5, max_entries=256, show_spinner=False)
def _cached_text(path_text: str, modified_ns: int) -> str:
    del modified_ns
    return Path(path_text).read_text(encoding="utf-8")


@st.cache_data(ttl=5, max_entries=256, show_spinner=False)
def _cached_table(path_text: str, modified_ns: int) -> pd.DataFrame:
    del modified_ns
    return pd.read_csv(Path(path_text))


def validate_client_id(value: Any) -> str:
    client_id = str(value or "").strip()
    if not CLIENT_ID_PATTERN.fullmatch(client_id):
        raise ValueError(
            "Client ID must be 1-64 lowercase letters, numbers, hyphens or "
            "underscores, and must start with a letter or number"
        )
    return client_id


def _metadata_client_id(document: dict[str, Any]) -> str | None:
    try:
        return validate_client_id(document.get("client_id"))
    except ValueError:
        return None


def _ids_from_keys(
    keys: list[str], client_id: str, collection: str, artifact: str,
) -> list[str]:
    prefix = f"{client_id}/{collection}/"
    suffix = f"/{artifact}"
    return sorted({
        key[len(prefix):-len(suffix)]
        for key in keys
        if key.startswith(prefix)
        and key.endswith(suffix)
        and "/" not in key[len(prefix):-len(suffix)]
    })


class Catalogue:
    """Small read-only facade over DataPlatform's governed local storage."""

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
            raise ValueError(
                f"Artifact reference escapes governed storage: {area}/{key}"
            )
        return candidate

    def _read_json(self, area: str, key: str) -> dict[str, Any]:
        path = self._path(area, key)
        try:
            value = json.loads(
                _cached_text(str(path), path.stat().st_mtime_ns)
            )
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
            for path in search_path.rglob("*") if path.is_file()
        )

    @staticmethod
    def _owned(document: dict[str, Any], client_id: str, key: str):
        if _metadata_client_id(document) != client_id:
            raise MetadataReadError(
                f"Metadata ownership does not match {key}"
            )
        return document

    def list_clients(self) -> list[str]:
        """Return clients represented by authoritative or inbox evidence."""

        clients = set()
        for key in self._list_files("metadata"):
            parts = PurePosixPath(key).parts
            if len(parts) == 2 and parts[1] == "client.json":
                try:
                    client_id = validate_client_id(parts[0])
                    document = self._read_json("metadata", key)
                    self._owned(document, client_id, key)
                    clients.add(client_id)
                except (ValueError, MetadataReadError):
                    continue
            elif (
                len(parts) >= 4
                and parts[1] in {
                    "runs", "snapshots", "comparisons", "trends",
                    "interpretations",
                }
            ):
                try:
                    clients.add(validate_client_id(parts[0]))
                except ValueError:
                    continue
        raw_root = self._area_root("raw")
        if raw_root.is_dir():
            for path in raw_root.iterdir():
                if not path.is_dir():
                    continue
                try:
                    clients.add(validate_client_id(path.name))
                except ValueError:
                    continue
        return sorted(clients)

    def list_runs(
        self, client_id: str | None = None,
    ) -> list[dict[str, Any]]:
        clients = (
            [validate_client_id(client_id)]
            if client_id else self.list_clients()
        )
        runs = []
        for owner in clients:
            keys = self._list_files("metadata", f"{owner}/runs")
            for run_id in _ids_from_keys(keys, owner, "runs", "run.json"):
                key = f"{owner}/runs/{run_id}/run.json"
                runs.append(self._owned(
                    self._read_json("metadata", key), owner, key
                ))
        return sorted(
            runs,
            key=lambda item: (
                str(item.get("started_at") or ""),
                str(item.get("run_id") or ""),
            ),
            reverse=True,
        )

    def list_snapshots(
        self, client_id: str | None = None,
    ) -> list[dict[str, Any]]:
        clients = (
            [validate_client_id(client_id)]
            if client_id else self.list_clients()
        )
        snapshots = []
        for owner in clients:
            keys = self._list_files("metadata", f"{owner}/snapshots")
            for snapshot_id in _ids_from_keys(
                keys, owner, "snapshots", "snapshot.json"
            ):
                key = f"{owner}/snapshots/{snapshot_id}/snapshot.json"
                snapshots.append(self._owned(
                    self._read_json("metadata", key), owner, key
                ))
        return sorted(
            snapshots,
            key=lambda item: (
                str(item.get("observation_date") or ""),
                str(item.get("snapshot_id") or ""),
            ),
            reverse=True,
        )

    def _owner_for(
        self, collection: str, identity: str, artifact: str,
    ) -> str:
        matches = [
            client_id for client_id in self.list_clients()
            if self._path(
                "metadata",
                f"{client_id}/{collection}/{identity}/{artifact}",
            ).is_file()
        ]
        if not matches:
            raise FileNotFoundError(identity)
        if len(matches) > 1:
            raise MetadataReadError(
                f"{identity} is ambiguous across clients: {matches}"
            )
        return matches[0]

    def snapshot_bundle(
        self, snapshot_id: str, client_id: str | None = None,
    ) -> dict[str, dict[str, Any]]:
        owner = (
            validate_client_id(client_id)
            if client_id
            else self._owner_for("snapshots", snapshot_id, "snapshot.json")
        )
        base = f"{owner}/snapshots/{snapshot_id}"
        snapshot = self._owned(
            self._read_json("metadata", f"{base}/snapshot.json"),
            owner,
            f"{base}/snapshot.json",
        )
        bundle = {"snapshot": snapshot}
        for name in ("fitness", "diagnosis", "findings"):
            try:
                document = self._read_json(
                    "metadata", f"{base}/{name}.json"
                )
                bundle[name] = self._owned(
                    document, owner, f"{base}/{name}.json"
                )
            except FileNotFoundError:
                bundle[name] = {}
        return bundle

    def list_products(
        self,
        collection: str,
        artifact: str,
        client_id: str | None = None,
    ) -> list[dict[str, Any]]:
        clients = (
            [validate_client_id(client_id)]
            if client_id else self.list_clients()
        )
        products = []
        for owner in clients:
            keys = self._list_files("metadata", f"{owner}/{collection}")
            for identity in reversed(
                _ids_from_keys(keys, owner, collection, artifact)
            ):
                key = f"{owner}/{collection}/{identity}/{artifact}"
                products.append(self._owned(
                    self._read_json("metadata", key), owner, key
                ))
        return products

    def list_comparisons(self, client_id: str | None = None):
        return self.list_products(
            "comparisons", "comparison.json", client_id
        )

    def list_trends(self, client_id: str | None = None):
        return self.list_products("trends", "trend.json", client_id)

    def list_interpretations(self, client_id: str | None = None):
        return self.list_products(
            "interpretations", "session.json", client_id
        )

    def read_artifact(self, reference: str) -> str:
        path = PurePosixPath(reference)
        if len(path.parts) < 2:
            raise ValueError(
                f"Unsupported artifact reference: {reference}"
            )
        area = path.parts[0]
        key = "/".join(path.parts[1:])
        try:
            target = self._path(area, key)
            return _cached_text(str(target), target.stat().st_mtime_ns)
        except (OSError, UnicodeError) as error:
            raise MetadataReadError(
                f"Artifact could not be read: {reference} ({error})"
            ) from error

    def read_table(self, reference: str) -> pd.DataFrame:
        path = PurePosixPath(reference)
        if len(path.parts) < 2:
            raise ValueError(
                f"Unsupported artifact reference: {reference}"
            )
        try:
            target = self._path(
                path.parts[0], "/".join(path.parts[1:])
            )
            return _cached_table(str(target), target.stat().st_mtime_ns)
        except (OSError, UnicodeError, pd.errors.ParserError) as error:
            raise MetadataReadError(
                f"Tabular artifact could not be read: {reference} ({error})"
            ) from error

    def read_snapshot_dataset(
        self, snapshot: dict[str, Any], dataset: str,
    ) -> pd.DataFrame:
        reference = snapshot.get("datasets", {}).get(dataset)
        if not reference:
            raise ValueError(
                f"Snapshot does not reference a {dataset!r} dataset"
            )
        path = PurePosixPath(str(reference))
        governed = (
            path.as_posix()
            if path.parts and path.parts[0] in {
                "raw", "processed", "curated", "metadata",
            }
            else f"processed/{path.as_posix()}"
        )
        return self.read_table(governed)


def flatten_fitness(fitness: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for capability, assessment in fitness.get(
        "capabilities", {}
    ).items():
        rows.append({
            "Capability": capability.replace("_", " ").title(),
            "Assessment": assessment.get(
                "status", "unknown"
            ).replace("_", " ").title(),
            "Blockers": len(
                assessment.get("blocking_conditions", [])
            ),
            "Caveats": len(assessment.get("caveats", [])),
            "Unavailable rules": len(
                assessment.get("unavailable_rules", [])
            ),
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
            "Affected entities": sum(
                len(values) for values in entities.values()
            ),
            "Rule": finding.get("rule_id"),
        })
    return pd.DataFrame(rows)
