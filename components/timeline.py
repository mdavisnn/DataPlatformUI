"""Altair composition for the diagnostic plan-on-a-page view."""

from __future__ import annotations

from typing import Any

import altair as alt
import pandas as pd


SEVERITY_DOMAIN = ["Low", "Medium", "High", "Unknown"]
SEVERITY_RANGE = ["#16a34a", "#d97706", "#dc2626", "#64748b"]


def diagnostic_timeline_chart(
    schedule: pd.DataFrame,
    occurrences: pd.DataFrame,
    observation_date: Any,
) -> alt.LayerChart:
    """Build a forecast timeline with dated finding evidence overlaid."""

    y_encoding = alt.Y(
        "Lane:N",
        sort=alt.SortField(field="LaneOrder", order="ascending"),
        title=None,
        axis=alt.Axis(labelLimit=360, labelPadding=8),
    )
    x_axis = alt.Axis(title="Forecast timeline", format="%b %Y", grid=True)

    tasks = schedule.loc[~schedule["IsMilestone"]]
    milestones = schedule.loc[schedule["IsMilestone"]]
    layers: list[alt.Chart] = []

    if not tasks.empty:
        layers.append(
            alt.Chart(tasks)
            .mark_bar(size=18, cornerRadius=3, color="#94a3b8")
            .encode(
                x=alt.X("ForecastStartDate:T", axis=x_axis),
                x2="PlotFinish:T",
                y=y_encoding,
                tooltip=[
                    alt.Tooltip("TaskID:N", title="Task ID"),
                    alt.Tooltip("TaskName:N", title="Task"),
                    alt.Tooltip("Status:N", title="Status"),
                    alt.Tooltip(
                        "PercentComplete:Q",
                        title="Complete",
                        format=".0f",
                    ),
                    alt.Tooltip(
                        "ForecastStartDate:T", title="Forecast start"
                    ),
                    alt.Tooltip(
                        "ForecastFinishDate:T", title="Forecast finish"
                    ),
                ],
            )
        )

    if not milestones.empty:
        layers.append(
            alt.Chart(milestones)
            .mark_point(
                shape="diamond",
                filled=True,
                size=120,
                color="#334155",
            )
            .encode(
                x=alt.X("ForecastFinishDate:T", axis=x_axis),
                y=y_encoding,
                tooltip=[
                    alt.Tooltip("TaskID:N", title="Milestone ID"),
                    alt.Tooltip("TaskName:N", title="Milestone"),
                    alt.Tooltip(
                        "ForecastFinishDate:T", title="Forecast date"
                    ),
                ],
            )
        )

    finding_pick = alt.selection_point(
        name="finding_pick",
        fields=["FindingID"],
        on="click",
        clear="dblclick",
        empty=False,
    )
    if not occurrences.empty:
        ranges = occurrences.loc[occurrences["OccurrenceType"] == "range"]
        points = occurrences.loc[occurrences["OccurrenceType"] == "point"]
        color = alt.Color(
            "Severity:N",
            scale=alt.Scale(domain=SEVERITY_DOMAIN, range=SEVERITY_RANGE),
            legend=alt.Legend(title="Finding severity"),
        )
        finding_tooltip = [
            alt.Tooltip("Title:N", title="Finding"),
            alt.Tooltip("RuleID:N", title="Rule"),
            alt.Tooltip("Domain:N", title="Domain"),
            alt.Tooltip("Severity:N", title="Severity"),
            alt.Tooltip("TaskID:N", title="Task ID"),
            alt.Tooltip("Start:T", title="Evidence start"),
            alt.Tooltip("Finish:T", title="Evidence finish"),
            alt.Tooltip("Detail:N", title="Evidence"),
        ]
        if not ranges.empty:
            layers.append(
                alt.Chart(ranges)
                .mark_bar(size=9, cornerRadius=2, stroke="#ffffff")
                .encode(
                    x=alt.X("Start:T", axis=x_axis),
                    x2="PlotFinish:T",
                    y=y_encoding,
                    color=color,
                    opacity=alt.condition(
                        finding_pick, alt.value(1), alt.value(0.82)
                    ),
                    tooltip=finding_tooltip,
                )
            )
        if not points.empty:
            layers.append(
                alt.Chart(points)
                .mark_point(filled=True, size=145, stroke="#ffffff")
                .encode(
                    x=alt.X("MarkerDate:T", axis=x_axis),
                    y=y_encoding,
                    color=color,
                    shape=alt.Shape(
                        "Domain:N",
                        scale=alt.Scale(
                            domain=["Schedule", "Resource", "Data"],
                            range=["triangle-up", "square", "diamond"],
                        ),
                        legend=alt.Legend(title="Finding domain"),
                    ),
                    opacity=alt.condition(
                        finding_pick, alt.value(1), alt.value(0.9)
                    ),
                    tooltip=finding_tooltip,
                )
            )

    observed = pd.to_datetime(observation_date, errors="coerce")
    if pd.notna(observed):
        layers.append(
            alt.Chart(pd.DataFrame({"ObservationDate": [observed]}))
            .mark_rule(color="#0284c7", strokeDash=[5, 4], size=2)
            .encode(
                x=alt.X("ObservationDate:T", axis=x_axis),
                tooltip=[
                    alt.Tooltip(
                        "ObservationDate:T", title="Observation date"
                    )
                ],
            )
        )

    chart = alt.layer(*layers)
    if not occurrences.empty:
        chart = chart.add_params(finding_pick)
    return (
        chart.properties(height=max(320, len(schedule) * 38))
        .configure_view(strokeWidth=0)
        .configure_axis(labelFontSize=12, titleFontSize=12)
    )
