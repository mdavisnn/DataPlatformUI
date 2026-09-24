"""Read-only distributions and interestingness lens."""

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from components.console import render_hero, render_metric_row
from services.console_context import console_context
from services.lenses import diagnostic_outcome, product_reference
from services.platform_reader import MetadataReadError


MEASURE_GUIDANCE = {
    ("Project", "TaskCount"): (
        "Number of tasks",
        "The number of canonical tasks linked to each project.",
    ),
    ("Project", "ProjectDurationDays"): (
        "Forecast project duration",
        "Calendar days between the project's forecast start and forecast "
        "finish dates.",
    ),
    ("Project", "MedianActivityDurationDays"): (
        "Typical task duration",
        "The median forecast duration of tasks in each project. The median "
        "reduces the influence of a few unusually long tasks.",
    ),
    ("Project", "MilestoneDensityPct"): (
        "Milestone share",
        "The percentage of a project's tasks recorded as milestones.",
    ),
    ("Project", "DependencyCoveragePct"): (
        "Tasks connected by dependencies",
        "The percentage of project tasks that appear as a predecessor or "
        "successor in the dependency evidence.",
    ),
    ("Project", "ResourceCount"): (
        "Assigned people",
        "The number of distinct resources assigned to tasks in each project.",
    ),
    ("Resource", "ProjectCount"): (
        "Projects per person",
        "The number of distinct projects to which each person is assigned.",
    ),
    ("Resource", "AssignmentCount"): (
        "Assignments per person",
        "The number of valid task-assignment records for each person.",
    ),
    ("Resource", "AllocationSharePct"): (
        "Share of planned allocation",
        "The person's share of all recorded assignment allocation in this "
        "observation. It is not actual utilisation.",
    ),
}


def _measure_guidance(entity_type, metric):
    return MEASURE_GUIDANCE.get(
        (entity_type, metric),
        (
            str(metric).replace("_", " "),
            "A saved measure produced by DataPlatform for this observation.",
        ),
    )


def _read_product(catalogue, outcome, name):
    reference = product_reference(outcome, name)
    if not reference:
        raise ValueError(f"Exploratory product {name!r} is not recorded")
    return catalogue.read_table(reference)


_, catalogue, client_id, snapshot = console_context()

render_hero(
    "Exploratory diagnostic",
    "Distributions and interestingness",
    "See the shape of portfolio evidence and inspect values that fall outside "
    "explainable IQR fences. Unusual means different, not necessarily poor.",
    icon=":material/scatter_plot:",
)

if not snapshot:
    st.info("No diagnosed observation is available.")
    st.stop()

snapshot_id = snapshot["snapshot_id"]
bundle = catalogue.snapshot_bundle(snapshot_id, client_id)
outcome = diagnostic_outcome(bundle["diagnosis"], "exploratory")
if not outcome or outcome.get("status") != "success":
    st.info(
        "Distribution analysis is unavailable for this observation. Run a "
        "current diagnosis or review exploratory capability fitness."
    )
    st.stop()

try:
    observations = _read_product(catalogue, outcome, "observations")
    summary = _read_product(
        catalogue, outcome, "distribution_summary"
    )
    interestingness = _read_product(
        catalogue, outcome, "interestingness"
    )
except (FileNotFoundError, ValueError, MetadataReadError) as error:
    st.warning(f"Exploratory evidence is unavailable: {error}")
    st.stop()

metrics = outcome.get("metrics", {})
render_metric_row([
    ("Distributions", metrics.get("distribution_count")),
    ("Evidence values", metrics.get("observation_count")),
    ("Unusual values", metrics.get("interesting_value_count")),
    ("Unusual projects", metrics.get("unusual_projects")),
    ("Unusual resources", metrics.get("unusual_resources")),
])

if observations.empty:
    st.info("No distribution observations are available for this snapshot.")
    st.stop()

filters = st.columns(2)
entity_types = sorted(
    observations.get("EntityType", pd.Series(dtype=str))
    .dropna().astype(str).unique().tolist()
)
entity_type = filters[0].segmented_control(
    "Entity type",
    entity_types,
    default=entity_types[0] if entity_types else None,
    key=f"patterns_entity_{snapshot_id}",
)
metrics_available = sorted(
    observations.loc[
        observations["EntityType"] == entity_type, "Metric"
    ].dropna().astype(str).unique().tolist()
)
metric = filters[1].selectbox(
    "Measure",
    metrics_available,
    format_func=lambda value: _measure_guidance(
        entity_type, value
    )[0],
    key=f"patterns_metric_{snapshot_id}",
)
measure_label, measure_explanation = _measure_guidance(
    entity_type, metric
)
st.caption(measure_explanation)
with st.expander("Measure glossary", icon=":material/menu_book:"):
    for glossary_metric in metrics_available:
        glossary_label, glossary_explanation = _measure_guidance(
            entity_type, glossary_metric
        )
        st.markdown(
            f"**{glossary_label}**  {glossary_explanation}"
        )

values = observations[
    (observations["EntityType"] == entity_type)
    & (observations["Metric"] == metric)
].copy()
distribution = summary[
    (summary["EntityType"] == entity_type)
    & (summary["Metric"] == metric)
].copy()

histogram_column, ranked_column = st.columns(2)
with histogram_column:
    st.subheader("Distribution")
    if values.empty:
        st.info("No evidence values are available for this measure.")
    else:
        histogram = (
            alt.Chart(values)
            .mark_bar(color="#46637f")
            .encode(
                x=alt.X(
                    "Value:Q",
                    bin=alt.Bin(maxbins=12),
                    title=measure_label,
                ),
                y=alt.Y("count():Q", title="Entities"),
                tooltip=[
                    alt.Tooltip(
                        "Value:Q", bin=alt.Bin(maxbins=12),
                        title="Value band",
                    ),
                    alt.Tooltip("count():Q", title="Entities"),
                ],
            )
        )
        st.altair_chart(histogram, width="stretch")
with ranked_column:
    st.subheader("Ranked evidence")
    if values.empty:
        st.info("No ranked values are available for this measure.")
    else:
        ranked = (
            alt.Chart(values)
            .mark_bar(color="#6f879f")
            .encode(
                x=alt.X("Value:Q", title=measure_label),
                y=alt.Y(
                    "EntityName:N",
                    sort="-x",
                    title=None,
                ),
                tooltip=[
                    "EntityName:N", "EntityID:N", "Value:Q",
                    "PercentileRank:Q",
                ],
            )
        )
        st.altair_chart(ranked, width="stretch")

st.subheader("Distribution evidence")
st.caption(
    "Summarises the selected measure across comparable projects or people. "
    "It shows the typical value, range, quartiles, evidence coverage and the "
    "IQR boundaries used to identify unusually high or low observations."
)
if distribution.empty:
    st.info("No distribution summary is available for this measure.")
else:
    st.dataframe(distribution, hide_index=True, width="stretch")

st.subheader("What is unusual?")
entity_signals = interestingness[
    interestingness["EntityType"] == entity_type
]
if entity_signals.empty:
    st.info(
        "No values for this entity type fell outside a configured IQR fence."
    )
else:
    st.dataframe(
        entity_signals[[
            "EntityName", "EntityID", "Metric", "Value",
            "PopulationMedian", "PercentileRank", "Direction",
            "RatioToMedian", "RuleID", "Explanation",
        ]],
        hide_index=True,
        width="stretch",
    )

with st.expander("Method and limits"):
    st.write(metrics.get("method", "IQR fence method."))
    st.caption(
        f"IQR multiplier: {metrics.get('iqr_multiplier')}; minimum "
        f"population: {metrics.get('minimum_population')}."
    )
    unavailable = metrics.get("unavailable_metrics", [])
    if unavailable:
        st.caption(
            "Unavailable measures: "
            + ", ".join(str(item) for item in unavailable)
            + "."
        )
    st.caption(
        "No composite score is calculated. A flagged value is evidence for "
        "investigation and does not establish risk, cause or poor performance."
    )
