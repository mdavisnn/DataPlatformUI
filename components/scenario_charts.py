"""Visual comparisons for deterministic SchedulePlatform results."""

from __future__ import annotations

import altair as alt
import pandas as pd


_SCHEDULE_DOMAIN = ["Baseline", "Scenario"]
_SCHEDULE_COLORS = ["#94a3b8", "#0284c7"]


def scenario_project_timeline(frame: pd.DataFrame) -> alt.Chart:
    """Compare baseline and selected-scenario project windows."""

    return (
        alt.Chart(frame)
        .mark_bar(size=18, cornerRadius=3)
        .encode(
            x=alt.X(
                "Start:T",
                title="Calculated calendar-day schedule",
                axis=alt.Axis(format="%b %Y", grid=True),
            ),
            x2="PlotFinish:T",
            y=alt.Y(
                "Lane:N",
                sort=alt.SortField(
                    field="LaneOrder", order="ascending"
                ),
                title=None,
                axis=alt.Axis(labelLimit=420, labelPadding=8),
            ),
            color=alt.Color(
                "Schedule:N",
                scale=alt.Scale(
                    domain=_SCHEDULE_DOMAIN,
                    range=_SCHEDULE_COLORS,
                ),
                legend=alt.Legend(title=None),
            ),
            tooltip=[
                alt.Tooltip("ProjectID:N", title="Project ID"),
                alt.Tooltip("ProjectName:N", title="Project"),
                alt.Tooltip("Schedule:N", title="Schedule"),
                alt.Tooltip("Start:T", title="Start"),
                alt.Tooltip("Finish:T", title="Finish"),
                alt.Tooltip(
                    "Finish movement (days):Q",
                    title="Finish movement (days)",
                ),
            ],
        )
        .properties(height=max(320, len(frame) * 21))
        .configure_view(strokeWidth=0)
        .configure_axis(labelFontSize=12, titleFontSize=12)
    )


def scenario_resource_load_chart(frame: pd.DataFrame) -> alt.Chart:
    """Compare baseline and scenario load for each affected resource."""

    resource_field = "Resource" if "Resource" in frame else "ResourceID"
    base = alt.Chart(frame).encode(
        x=alt.X(
            "Date:T",
            title=None,
            axis=alt.Axis(format="%d %b", grid=True),
        ),
        tooltip=[
            alt.Tooltip(f"{resource_field}:N", title="Resource"),
            alt.Tooltip("Schedule:N", title="Schedule"),
            alt.Tooltip("Date:T", title="Date", format="%d %b %Y"),
            alt.Tooltip("Allocation:Q", title="Allocation (%)", format=".0f"),
            alt.Tooltip("Capacity:Q", title="Capacity (%)", format=".0f"),
            alt.Tooltip("Over capacity:N", title="Over capacity"),
        ],
    )
    loads = base.mark_line(
        interpolate="step-after",
        strokeWidth=3,
    ).encode(
        y=alt.Y(
            "Allocation:Q",
            title="Allocation / capacity (%)",
            scale=alt.Scale(zero=True),
        ),
        color=alt.Color(
            "Schedule:N",
            scale=alt.Scale(
                domain=_SCHEDULE_DOMAIN,
                range=_SCHEDULE_COLORS,
            ),
            legend=alt.Legend(title=None, orient="top"),
        ),
        strokeDash=alt.StrokeDash(
            "Schedule:N",
            scale=alt.Scale(
                domain=_SCHEDULE_DOMAIN,
                range=[[6, 4], [1, 0]],
            ),
            legend=None,
        ),
    )
    capacity = (
        base.transform_filter(alt.datum.Schedule == "Baseline")
        .mark_line(
            interpolate="step-after",
            color="#dc2626",
            strokeDash=[3, 3],
            strokeWidth=1.5,
        )
        .encode(y=alt.Y("Capacity:Q"))
    )
    overloads = (
        base.transform_filter(alt.datum["Over capacity"] == True)
        .mark_point(color="#dc2626", filled=True, size=65)
        .encode(y=alt.Y("Allocation:Q"))
    )
    return (
        alt.layer(loads, capacity, overloads)
        .properties(height=145)
        .facet(
            row=alt.Row(
                f"{resource_field}:N",
                title=None,
                header=alt.Header(
                    labelAngle=0,
                    labelAlign="left",
                    labelFontSize=13,
                    labelFontWeight="bold",
                ),
            )
        )
        .resolve_scale(x="shared", y="shared")
        .configure_view(strokeWidth=0)
        .configure_axis(labelFontSize=12, titleFontSize=12)
    )
