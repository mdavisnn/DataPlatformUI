"""Historical comparison and trend views."""

import streamlit as st

from components.console import render_hero, render_metric_row
from services.console_context import console_context, governed_reference, safe
from services.platform_reader import MetadataReadError


_, catalogue, client_id, _ = console_context()

render_hero(
    "Compare & trend",
    "What changed—and what keeps happening?",
    "Historical products preserve the difference between observed movement and the consultant's interpretation of its significance.",
    icon=":material/timeline:",
)

comparisons = (
    safe(lambda: catalogue.list_comparisons(client_id), [])
    if client_id else []
)
trends = (
    safe(lambda: catalogue.list_trends(client_id), [])
    if client_id else []
)
comparison_tab, trend_tab = st.tabs(
    ["Two-observation comparison", "Trend window"], on_change="rerun"
)

if comparison_tab.open:
    with comparison_tab:
        if not comparisons:
            st.info("No historical comparisons are available.")
        for item in comparisons:
            with st.container(border=True):
                st.subheader(item.get("comparison_id", "Comparison"))
                render_metric_row([
                    ("From", item.get("from_observation_date")),
                    ("To", item.get("to_observation_date")),
                    ("Changes", item.get("change_count")),
                    ("Findings", item.get("finding_count")),
                ])
                reference = item.get("detailed_output")
                if reference:
                    try:
                        st.dataframe(
                            catalogue.read_table(governed_reference(reference)),
                            hide_index=True,
                        )
                    except (FileNotFoundError, ValueError, MetadataReadError) as error:
                        st.warning(f"Detailed comparison evidence is unavailable: {error}")

if trend_tab.open:
    with trend_tab:
        if not trends:
            st.info("No trend windows are available.")
        for item in trends:
            with st.container(border=True):
                st.subheader(item.get("trend_id", "Trend"))
                render_metric_row([
                    ("Observations", item.get("observation_count")),
                    ("Transitions", item.get("transition_count")),
                    ("Changes", item.get("change_count")),
                    ("Findings", item.get("finding_count")),
                ])
                st.caption(item.get("continuity_policy", ""))
                for reference in item.get("detailed_outputs", {}).values():
                    try:
                        st.dataframe(
                            catalogue.read_table(governed_reference(reference)),
                            hide_index=True,
                        )
                    except (FileNotFoundError, ValueError, MetadataReadError) as error:
                        st.warning(f"Detailed trend evidence is unavailable: {error}")
