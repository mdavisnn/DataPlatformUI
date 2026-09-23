"""Helpers for locating backend-owned point-in-time lens products."""

from __future__ import annotations

from typing import Any


def diagnostic_outcome(
    diagnosis: dict[str, Any],
    capability: str,
) -> dict[str, Any] | None:
    """Return the recorded outcome for a capability, when available."""

    return next(
        (
            item for item in diagnosis.get("diagnostics", [])
            if item.get("capability") == capability
        ),
        None,
    )


def product_reference(
    outcome: dict[str, Any],
    product: str,
) -> str | None:
    """Return a governed product reference without guessing list position."""

    reference = outcome.get("products", {}).get(product)
    return str(reference) if reference else None
