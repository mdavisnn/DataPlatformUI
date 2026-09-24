"""Altair charts for the resource lens."""

from __future__ import annotations

import altair as alt
import pandas as pd


def _display_text(value) -> str:
    """Return a clean display value for an optional scalar."""

    return "" if value is None or pd.isna(value) else str(value).strip()


def _resource_label(row: pd.Series) -> str:
    """Label a resource by name while retaining its unique identifier."""

    name = _display_text(row.get("ResourceName"))
    resource_id = _display_text(row.get("ResourceID"))
    if name and resource_id:
        return f"{name} \u00b7 {resource_id}"
    return name or resource_id or "Unknown resource"


def allocation_pressure_chart(
    pressure: pd.DataFrame,
    conflict_threshold_pct: float,
) -> alt.LayerChart:
    """Compare peak allocation using a unique resource lane."""

    chart_data = pressure.copy()
    chart_data["ResourceLabel"] = chart_data.apply(
        _resource_label,
        axis=1,
    )
    bars = (
        alt.Chart(chart_data)
        .mark_bar(color="#46637f")
        .encode(
            x=alt.X(
                "PeakConcurrentAllocationPct:Q",
                title="Peak concurrent assignment allocation (%)",
            ),
            y=alt.Y(
                "ResourceLabel:N",
                sort="-x",
                title=None,
                axis=alt.Axis(labelLimit=360, labelPadding=8),
            ),
            tooltip=[
                alt.Tooltip("ResourceName:N", title="Person"),
                alt.Tooltip("ResourceID:N", title="Resource ID"),
                alt.Tooltip(
                    "PeakConcurrentAllocationPct:Q",
                    title="Peak allocation",
                ),
                alt.Tooltip("ProjectCount:Q", title="Projects"),
                alt.Tooltip(
                    "ConflictPeriodCount:Q", title="Conflict periods"
                ),
            ],
        )
    )
    threshold = alt.Chart(pd.DataFrame({
        "Threshold": [conflict_threshold_pct]
    })).mark_rule(color="#b94a48", strokeDash=[5, 4]).encode(
        x="Threshold:Q"
    )
    return bars + threshold
