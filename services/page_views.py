"""Compose existing Streamlit page scripts inside consolidated navigation pages."""

from __future__ import annotations

import runpy
from pathlib import Path

from components.console import suppress_page_hero


_PAGE_ROOT = (Path(__file__).parents[1] / "app_pages").resolve()
_PAGE_VIEWS = {
    "workspace": "workspace.py",
    "evidence": "evidence.py",
    "project_health": "project_health.py",
    "findings": "findings.py",
    "schedule": "schedule.py",
    "plan": "plan.py",
    "dependencies": "dependencies.py",
    "patterns": "patterns.py",
}


def run_page_view(view: str) -> None:
    """Render one allow-listed existing page script as the active page view."""
    filename = _PAGE_VIEWS.get(view)
    if filename is None:
        raise ValueError(f"Unknown page view: {view}")

    page_path = (_PAGE_ROOT / filename).resolve()
    if not page_path.is_relative_to(_PAGE_ROOT):
        raise ValueError(f"Page view resolves outside app_pages: {view}")

    with suppress_page_hero():
        runpy.run_path(
            str(page_path),
            run_name=f"__dataplatformui_view_{view}__",
        )
