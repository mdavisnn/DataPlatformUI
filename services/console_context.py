"""Shared context helpers for the consultant console pages."""

from __future__ import annotations

from typing import Any, Callable, TypeVar

import streamlit as st

from config.settings import Settings
from services.catalog import Catalogue
from services.platform_reader import MetadataReadError


T = TypeVar("T")


def safe(call: Callable[[], T], default: T) -> T:
    try:
        return call()
    except (FileNotFoundError, ValueError, KeyError, MetadataReadError):
        return default


def console_context() -> tuple[Settings, Catalogue, dict[str, Any] | None]:
    settings = Settings.from_environment()
    catalogue = Catalogue(settings)
    snapshot_id = st.session_state.get("selected_snapshot_id")
    snapshot = next(
        (
            item
            for item in safe(catalogue.list_snapshots, [])
            if item.get("snapshot_id") == snapshot_id
        ),
        None,
    )
    return settings, catalogue, snapshot


def governed_reference(reference: str) -> str:
    return reference if reference.startswith(("raw/", "processed/", "curated/", "metadata/")) else f"curated/{reference}"
