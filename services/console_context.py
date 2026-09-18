"""Shared context helpers for the consultant console pages."""

from __future__ import annotations

from typing import Any, Callable, TypeVar

import streamlit as st

from config.settings import Settings
from services.catalog import Catalogue, validate_client_id
from services.platform_reader import MetadataReadError


T = TypeVar("T")


def safe(call: Callable[[], T], default: T) -> T:
    try:
        return call()
    except (FileNotFoundError, ValueError, KeyError, MetadataReadError):
        return default


def console_context() -> tuple[
    Settings,
    Catalogue,
    str | None,
    dict[str, Any] | None,
]:
    settings = Settings.from_environment()
    catalogue = Catalogue(settings)
    supplied_client = st.session_state.get("selected_client_id")
    try:
        client_id = validate_client_id(supplied_client)
    except ValueError:
        client_id = None
    if client_id not in safe(catalogue.list_clients, []):
        client_id = None
    snapshot_id = st.session_state.get("selected_snapshot_id")
    snapshot = next(
        (
            item
            for item in safe(
                lambda: catalogue.list_snapshots(client_id),
                [],
            )
            if item.get("snapshot_id") == snapshot_id
        ),
        None,
    ) if client_id else None
    return settings, catalogue, client_id, snapshot


def governed_reference(reference: str) -> str:
    return reference if reference.startswith(("raw/", "processed/", "curated/", "metadata/")) else f"curated/{reference}"
