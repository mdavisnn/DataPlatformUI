"""Historical comparison and trend views."""

import streamlit as st

from components.console import render_hero, render_metric_row
from components.history_charts import delivery_trajectory_chart
from services.console_context import console_context, governed_reference, safe
from services.history import (
    delivery_project_facts,
    delivery_trajectory_metrics,
    prepare_delivery_trajectory,
    scope_delivery_trajectory,
    selected_trajectory_project_id,
)
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
                trend_id = str(item.get("trend_id", "trend"))
                from_date = item.get("from_observation_date", "Undated")
                to_date = item.get("to_observation_date", "Undated")
                st.subheader(
                    "Delivery trajectory",
                    icon=":material/trending_up:",
                )
                st.caption(
                    f"{from_date} → {to_date} · {trend_id} · "
                    f"{item.get('observation_count', 0)} governed observations "
                    f"· {item.get('transition_count', 0)} adjacent transitions"
                )

                references = item.get("detailed_outputs", {})
                tables = {}
                table_errors = []
                for name, reference in references.items():
                    try:
                        tables[name] = catalogue.read_table(
                            governed_reference(reference)
                        )
                    except (FileNotFoundError, ValueError, MetadataReadError) as error:
                        table_errors.append(str(error))

                observations = tables.get("project_observation_history")
                summary = tables.get("project_trend_summary")
                if observations is None or summary is None:
                    st.warning(
                        "Delivery trajectory is unavailable because the governed "
                        "observation history or trend summary could not be read."
                    )
                else:
                    try:
                        trajectory, excluded = prepare_delivery_trajectory(
                            observations,
                            summary,
                        )
                        metrics = delivery_trajectory_metrics(summary)
                    except ValueError as error:
                        st.warning(f"Delivery trajectory is unavailable: {error}")
                        trajectory = None

                    if trajectory is not None:
                        render_metric_row([
                            ("Projects moved", metrics["projects_moved"]),
                            ("Moved later", metrics["projects_slipped"]),
                            (
                                "Total days slipped",
                                metrics["total_days_slipped"],
                            ),
                            ("RAG changes", metrics["status_changes"]),
                        ])

                        if trajectory.empty:
                            st.info(
                                "No project observations have usable forecast "
                                "finish dates for this trend window."
                            )
                        else:
                            has_movers = bool(
                                trajectory["HadFinishMovement"].any()
                            )
                            scope = st.segmented_control(
                                "Project scope",
                                ["Forecast movers", "All projects"],
                                default=(
                                    "Forecast movers"
                                    if has_movers
                                    else "All projects"
                                ),
                                required=True,
                                key=f"history_scope_{trend_id}",
                            )
                            visible = scope_delivery_trajectory(
                                trajectory,
                                movers_only=scope == "Forecast movers",
                            )
                            chart_event = st.altair_chart(
                                delivery_trajectory_chart(visible),
                                width="stretch",
                                key=(
                                    f"history_trajectory_{trend_id}_{scope}"
                                ),
                                on_select="rerun",
                                selection_mode="trajectory_pick",
                            )
                            st.caption(
                                "Lines show forecast-finish movement from the "
                                "first observation in each continuous segment; "
                                "points show the reported RAG. Select a project "
                                "to inspect it. Double-click to clear the chart "
                                "selection."
                            )

                            project_rows = (
                                visible[["ProjectID", "DisplayName"]]
                                .drop_duplicates(subset=["ProjectID"])
                                .sort_values(["DisplayName", "ProjectID"])
                            )
                            project_labels = dict(
                                project_rows[
                                    ["ProjectID", "DisplayName"]
                                ].itertuples(index=False, name=None)
                            )
                            project_key = (
                                f"history_project_{trend_id}_{scope}"
                            )
                            chart_project_id = (
                                selected_trajectory_project_id(chart_event)
                            )
                            if chart_project_id in project_labels:
                                st.session_state[project_key] = chart_project_id
                            if (
                                st.session_state.get(project_key)
                                not in project_labels
                            ):
                                st.session_state[project_key] = next(
                                    iter(project_labels),
                                    None,
                                )

                            selected_project = st.selectbox(
                                "Inspect project",
                                list(project_labels),
                                format_func=project_labels.get,
                                key=project_key,
                            )
                            facts = delivery_project_facts(
                                visible,
                                selected_project,
                            )
                            if facts:
                                st.subheader(
                                    f"{facts['project_name']} · "
                                    f"{facts['project_id']}"
                                )
                                render_metric_row([
                                    (
                                        "Net forecast movement",
                                        (
                                            f"{facts['net_movement_days']:+d} "
                                            "days"
                                        ),
                                    ),
                                    (
                                        "Slippage transitions",
                                        facts["slippage_transitions"],
                                    ),
                                    (
                                        "Latest forecast finish",
                                        facts["latest_finish"].strftime(
                                            "%d %b %Y"
                                        ),
                                    ),
                                    (
                                        "Reported RAG",
                                        facts["status_path"],
                                    ),
                                ])
                                if facts["unavailable_transitions"]:
                                    st.caption(
                                        f"{facts['unavailable_transitions']} "
                                        "adjacent transition(s) were "
                                        "unavailable; the chart does not "
                                        "bridge those gaps."
                                    )

                        if excluded:
                            st.warning(
                                f"{excluded} observation row(s) were not "
                                "plotted because identity, dates or sequence "
                                "were unusable."
                            )

                if table_errors:
                    st.warning(
                        f"{len(table_errors)} governed trend artifact(s) "
                        "could not be read."
                    )

                if tables:
                    evidence = st.expander(
                        "Governed trend evidence",
                        icon=":material/database:",
                        on_change="rerun",
                    )
                    if evidence.open:
                        with evidence:
                            for name, table in tables.items():
                                st.markdown(
                                    f"**{name.replace('_', ' ').title()}**"
                                )
                                st.dataframe(table, hide_index=True)
