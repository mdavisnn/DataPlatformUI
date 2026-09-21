"""Altair charts for governed historical trend products."""

from __future__ import annotations

import altair as alt
import pandas as pd


RAG_DOMAIN = ["Green", "Amber", "Red", "Unknown"]
RAG_RANGE = ["#16a34a", "#d97706", "#dc2626", "#64748b"]


def delivery_trajectory_chart(trajectory: pd.DataFrame) -> alt.LayerChart:
    """Show forecast-finish movement with reported RAG at each observation."""

    trajectory_pick = alt.selection_point(
        name="trajectory_pick",
        fields=["ProjectID"],
        on="click",
        clear="dblclick",
        empty=False,
    )
    x = alt.X(
        "ObservationDate:T",
        title="Governed observation",
        axis=alt.Axis(format="%b %Y", labelAngle=0, grid=False),
    )
    y = alt.Y(
        "CumulativeMovementDays:Q",
        title="Forecast finish movement (days)",
        scale=alt.Scale(zero=True),
        axis=alt.Axis(grid=True),
    )
    tooltip = [
        alt.Tooltip("ProjectName:N", title="Project"),
        alt.Tooltip("ProjectID:N", title="Project ID"),
        alt.Tooltip("ObservationDate:T", title="Observation"),
        alt.Tooltip("FinishDate:T", title="Forecast finish"),
        alt.Tooltip(
            "CumulativeMovementDays:Q",
            title="Movement from segment start",
            format="+d",
        ),
        alt.Tooltip(
            "PeriodMovementDays:Q",
            title="Period movement",
            format="+d",
        ),
        alt.Tooltip("Status:N", title="Reported RAG"),
    ]

    zero = (
        alt.Chart(pd.DataFrame({"Reference": [0]}))
        .mark_rule(color="#64748b", strokeDash=[5, 4], opacity=0.7)
        .encode(y=alt.Y("Reference:Q"))
    )
    lines = (
        alt.Chart(trajectory)
        .mark_line(strokeWidth=2.5)
        .encode(
            x=x,
            y=y,
            detail="TrajectorySeries:N",
            color=alt.condition(
                trajectory_pick,
                alt.value("#0284c7"),
                alt.value("#94a3b8"),
            ),
            opacity=alt.condition(
                trajectory_pick,
                alt.value(1),
                alt.value(0.62),
            ),
            tooltip=tooltip,
        )
    )
    points = (
        alt.Chart(trajectory)
        .mark_point(
            filled=True,
            size=115,
            stroke="#ffffff",
            strokeWidth=1.5,
        )
        .encode(
            x=x,
            y=y,
            color=alt.Color(
                "Status:N",
                scale=alt.Scale(domain=RAG_DOMAIN, range=RAG_RANGE),
                legend=alt.Legend(title="Reported RAG"),
            ),
            opacity=alt.condition(
                trajectory_pick,
                alt.value(1),
                alt.value(0.88),
            ),
            tooltip=tooltip,
        )
    )
    labels = (
        alt.Chart(
            trajectory.loc[
                trajectory["IsLatest"] & trajectory["HadFinishMovement"]
            ]
        )
        .mark_text(
            align="left",
            baseline="middle",
            dx=8,
            fontSize=11,
        )
        .encode(
            x=x,
            y=y,
            text="EndLabel:N",
            color=alt.condition(
                trajectory_pick,
                alt.value("#0284c7"),
                alt.value("#475569"),
            ),
            opacity=alt.condition(
                trajectory_pick,
                alt.value(1),
                alt.value(0.84),
            ),
            tooltip=tooltip,
        )
    )
    return (
        alt.layer(zero, lines, points, labels)
        .add_params(trajectory_pick)
        .properties(height=430)
        .configure_view(strokeWidth=0)
        .configure_axis(labelFontSize=12, titleFontSize=12)
    )
