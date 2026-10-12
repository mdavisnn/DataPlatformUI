"""Altair views for governed DCMA schedule-assessment evidence."""

from __future__ import annotations

import altair as alt
import pandas as pd

from services.schedule_assessment import status_label


STATUS_DOMAIN = [
    "Outside tripwire",
    "Within threshold",
    "Not assessable",
]
STATUS_RANGE = ["#c2413b", "#16805b", "#64748b"]


def assessment_matrix_chart(frame: pd.DataFrame) -> alt.Chart:
    """Show one recorded result for each visible project and DCMA metric."""

    visible = frame.copy()
    visible["Metric"] = visible.apply(
        lambda row: f"{int(row['MetricNumber']):02d} · {row['MetricName']}",
        axis=1,
    )
    visible["Project"] = visible.apply(
        lambda row: (
            f"{row['ProjectName']} | {row['ProjectID']}"
            if pd.notna(row.get("ProjectName"))
            and str(row.get("ProjectName")).strip()
            else str(row["ProjectID"])
        ),
        axis=1,
    )
    visible["Result"] = visible["Status"].map(status_label)
    metric_order = (
        visible[["MetricNumber", "Metric"]]
        .drop_duplicates()
        .sort_values("MetricNumber")["Metric"]
        .tolist()
    )
    project_order = (
        visible[["Project", "ProjectID"]]
        .drop_duplicates()
        .sort_values("ProjectID")["Project"]
        .tolist()
    )
    return (
        alt.Chart(visible)
        .mark_rect(cornerRadius=2, stroke="white", strokeWidth=1)
        .encode(
            x=alt.X(
                "Metric:N",
                sort=metric_order,
                title="DCMA metric",
                axis=alt.Axis(labelAngle=-35, labelLimit=150),
            ),
            y=alt.Y(
                "Project:N",
                sort=project_order,
                title=None,
                axis=alt.Axis(labelLimit=240),
            ),
            color=alt.Color(
                "Result:N",
                title="Recorded result",
                scale=alt.Scale(domain=STATUS_DOMAIN, range=STATUS_RANGE),
            ),
            tooltip=[
                alt.Tooltip("Project:N", title="Project"),
                alt.Tooltip("Metric:N", title="Metric"),
                alt.Tooltip("Result:N", title="Result"),
                alt.Tooltip("Value:Q", title="Value"),
                alt.Tooltip("Unit:N", title="Unit"),
                alt.Tooltip("Comparison:N", title="Comparison"),
                alt.Tooltip("Threshold:Q", title="Tripwire"),
                alt.Tooltip(
                    "EvidenceCoveragePct:Q",
                    title="Evidence coverage (%)",
                ),
                alt.Tooltip("Reason:N", title="Limitation"),
            ],
        )
        .properties(height=max(220, len(project_order) * 38))
    )


def duration_distribution_chart(
    frame: pd.DataFrame,
    column: str,
    title: str,
) -> alt.Chart:
    """Plot a saved activity-duration measure without recalculation."""

    return (
        alt.Chart(frame)
        .mark_bar(color="#46637f")
        .encode(
            x=alt.X(
                f"{column}:Q",
                bin=alt.Bin(maxbins=14),
                title=title,
            ),
            y=alt.Y("count():Q", title="Activities"),
            tooltip=[
                alt.Tooltip(
                    f"{column}:Q",
                    bin=alt.Bin(maxbins=14),
                    title="Duration band",
                ),
                alt.Tooltip("count():Q", title="Activities"),
            ],
        )
        .properties(height=320)
    )
