"""Altair views for governed project-profile evidence."""

from __future__ import annotations

import altair as alt
import pandas as pd


STATUS_DOMAIN = ["Significant", "Attention", "No finding"]
STATUS_RANGE = ["#c2413b", "#d2872c", "#55738d"]
DOMAIN_COLORS = {
    "Portfolio": "#6b7280",
    "Schedule": "#b45309",
    "Resources": "#2563a6",
    "Dependencies": "#6d4ca5",
}


def attention_map_chart(frame: pd.DataFrame) -> alt.LayerChart:
    """Plot schedule and resource pressure with dependency context."""

    visible = frame[frame["Plottable"]].copy()
    selection = alt.selection_point(
        name="project_select",
        fields=["ProjectID"],
        on="click",
        clear="dblclick",
    )
    x_median = float(visible["ScheduleMedian"].dropna().iloc[0])
    y_median = float(visible["ResourceMedian"].dropna().iloc[0])
    vertical = (
        alt.Chart(pd.DataFrame({"Median": [x_median]}))
        .mark_rule(color="#94a3b8", strokeDash=[5, 5])
        .encode(x=alt.X("Median:Q"))
    )
    horizontal = (
        alt.Chart(pd.DataFrame({"Median": [y_median]}))
        .mark_rule(color="#94a3b8", strokeDash=[5, 5])
        .encode(y=alt.Y("Median:Q"))
    )
    points = (
        alt.Chart(visible)
        .mark_point(filled=True, stroke="white", strokeWidth=1.5)
        .encode(
            x=alt.X(
                "ScheduleConditionPct:Q",
                title="Tasks with schedule conditions (%)",
                scale=alt.Scale(domain=[0, 100]),
            ),
            y=alt.Y(
                "ConflictResourcePct:Q",
                title="Resources with conflicts (%)",
                scale=alt.Scale(domain=[0, 100]),
            ),
            size=alt.Size(
                "ConnectivityBubble:Q",
                title="Average task connectivity",
                scale=alt.Scale(range=[140, 1200]),
            ),
            shape=alt.Shape(
                "DependencyEvidence:N",
                title="Dependency evidence",
                scale=alt.Scale(
                    domain=["Available", "Unavailable"],
                    range=["circle", "diamond"],
                ),
            ),
            color=alt.Color(
                "FindingStatus:N",
                title="Finding status",
                scale=alt.Scale(domain=STATUS_DOMAIN, range=STATUS_RANGE),
            ),
            opacity=alt.condition(selection, alt.value(1), alt.value(0.62)),
            tooltip=[
                alt.Tooltip("ProjectLabel:N", title="Project"),
                alt.Tooltip(
                    "ScheduleConditionPct:Q",
                    title="Schedule condition tasks",
                    format=".1f",
                ),
                alt.Tooltip(
                    "ConflictResourcePct:Q",
                    title="Conflict resources",
                    format=".1f",
                ),
                alt.Tooltip(
                    "AverageConnectivity:Q",
                    title="Average connectivity",
                    format=".2f",
                ),
                alt.Tooltip("RAGStatus:N", title="Reported RAG"),
                alt.Tooltip("FindingCount:Q", title="Findings"),
                alt.Tooltip("DataFitness:N", title="Data fitness"),
            ],
        )
        .add_params(selection)
    )
    return (vertical + horizontal + points).properties(height=430)


def project_fingerprint_chart(frame: pd.DataFrame) -> alt.LayerChart:
    """Show one project's relative position without creating a score."""

    available = frame[
        frame["Availability"].eq("Available")
        & frame["PercentileRank"].notna()
    ].copy()
    measure_order = available["MetricLabel"].tolist()
    y = alt.Y(
        "MetricLabel:N",
        title=None,
        sort=measure_order,
        axis=alt.Axis(labelLimit=230),
    )
    domain = list(DOMAIN_COLORS)
    colors = [DOMAIN_COLORS[item] for item in domain]
    band = (
        alt.Chart(available)
        .mark_bar(color="#dbe3ea", size=18, cornerRadius=8)
        .encode(
            x=alt.X(
                "QuartileStart:Q",
                title="Percentile within this observation",
                scale=alt.Scale(domain=[0, 100]),
            ),
            x2="QuartileEnd:Q",
            y=y,
        )
    )
    median = (
        alt.Chart(available)
        .mark_tick(color="#64748b", thickness=2, size=25)
        .encode(x="PortfolioMedian:Q", y=y)
    )
    points = (
        alt.Chart(available)
        .mark_point(filled=True, size=130, stroke="white", strokeWidth=1.5)
        .encode(
            x=alt.X(
                "PercentileRank:Q",
                title="Percentile within this observation",
                scale=alt.Scale(domain=[0, 100]),
            ),
            y=y,
            color=alt.Color(
                "Domain:N",
                scale=alt.Scale(domain=domain, range=colors),
                title="Domain",
            ),
            shape=alt.Shape(
                "Unusual:N",
                title="IQR context",
                scale=alt.Scale(
                    domain=["Within IQR", "Outside IQR"],
                    range=["circle", "diamond"],
                ),
            ),
            tooltip=[
                alt.Tooltip("MetricLabel:N", title="Measure"),
                alt.Tooltip("ValueLabel:N", title="Value"),
                alt.Tooltip("PercentileRank:Q", title="Percentile", format=".1f"),
                alt.Tooltip("Median:Q", title="Portfolio median", format=".2f"),
                alt.Tooltip("PopulationCount:Q", title="Projects compared"),
                alt.Tooltip("Unusual:N", title="IQR context"),
            ],
        )
    )
    labels = (
        alt.Chart(available)
        .mark_text(align="left", dx=8, color="#475569")
        .encode(x="LabelPosition:Q", y=y, text="ValueLabel:N")
    )
    height = max(260, 38 * len(available))
    return (band + median + points + labels).properties(height=height)
