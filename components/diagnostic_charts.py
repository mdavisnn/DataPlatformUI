"""Compact charts for governed diagnostic Finding summaries."""

from __future__ import annotations

import altair as alt
import pandas as pd


SEVERITY_DOMAIN = ["High", "Medium", "Low"]
SEVERITY_RANGE = ["#dc2626", "#d97706", "#64748b"]


def severity_distribution_chart(
    frame: pd.DataFrame,
) -> alt.Chart:
    """Render a compact semantic severity strip from saved counts."""

    plot = frame.copy()
    plot["SeverityOrder"] = plot["Severity"].map(
        {value: index for index, value in enumerate(SEVERITY_DOMAIN)}
    )
    return (
        alt.Chart(plot)
        .mark_bar(cornerRadius=5)
        .encode(
            x=alt.X("Findings:Q", title="Findings", stack="zero"),
            color=alt.Color(
                "Severity:N",
                title="Severity",
                scale=alt.Scale(
                    domain=SEVERITY_DOMAIN,
                    range=SEVERITY_RANGE,
                ),
            ),
            order=alt.Order(
                "SeverityOrder:Q",
                sort="ascending",
            ),
            tooltip=[
                alt.Tooltip("Severity:N", title="Severity"),
                alt.Tooltip("Findings:Q", title="Findings"),
            ],
        )
        .properties(height=90)
        .configure_view(strokeWidth=0)
    )


def domain_distribution_chart(frame: pd.DataFrame) -> alt.Chart:
    """Render Finding concentration by diagnostic domain."""

    height = max(180, 34 * len(frame))
    return (
        alt.Chart(frame)
        .mark_bar(color="#123b63", cornerRadiusEnd=4)
        .encode(
            x=alt.X("Findings:Q", title="Findings"),
            y=alt.Y(
                "Domain:N",
                title=None,
                sort=alt.SortField("Findings", order="descending"),
            ),
            tooltip=[
                alt.Tooltip("Domain:N", title="Domain"),
                alt.Tooltip("Findings:Q", title="Findings"),
            ],
        )
        .properties(height=height)
        .configure_view(strokeWidth=0)
    )
