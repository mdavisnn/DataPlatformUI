"""Historical comparison and trend views."""

from __future__ import annotations

import json
from typing import Any

import streamlit as st

from components.console import (
    MetricCard,
    render_finding,
    render_hero,
    render_metric_row,
    render_panel,
)
from components.history_charts import delivery_trajectory_chart
from services.console_context import console_context, governed_reference, safe
from services.history import (
    delivery_project_facts,
    delivery_trajectory_metrics,
    history_fitness_counts,
    history_product_label,
    history_scope_frame,
    prepare_delivery_trajectory,
    scope_delivery_trajectory,
    selected_trajectory_project_id,
)
from services.platform_reader import MetadataReadError


def _metadata_reference(reference: str) -> str:
    if reference.startswith(("raw/", "processed/", "curated/", "metadata/")):
        return reference
    return f"metadata/{reference}"


def _recorded_findings(catalogue, product: dict[str, Any]):
    reference = product.get("findings_object")
    if not reference:
        return [], None
    try:
        document = json.loads(
            catalogue.read_artifact(_metadata_reference(str(reference)))
        )
    except (
        FileNotFoundError,
        ValueError,
        MetadataReadError,
        json.JSONDecodeError,
    ) as error:
        return [], str(error)
    if document.get("client_id") != product.get("client_id"):
        return [], "Finding metadata does not match the selected client."
    findings = document.get("findings", [])
    return findings if isinstance(findings, list) else [], None


def _render_comparability(product: dict[str, Any]) -> None:
    counts = history_fitness_counts(product)
    status = str(product.get("execution_status", "unknown"))
    badge_color = "orange" if "limitation" in status else "green"
    contract = product.get("comparability_contract", [])

    with render_panel(
        "Comparison boundary",
        "The saved contract and evidence-fitness limits for this historical product.",
        icon=":material/compare_arrows:",
    ):
        st.badge(
            status.replace("_", " ").title(),
            color=badge_color,
            icon=":material/verified:" if badge_color == "green" else ":material/warning:",
        )
        st.caption(
            "Saved comparability contract: "
            + (", ".join(map(str, contract)) if contract else "Not recorded")
        )
        render_metric_row([
            ("Fitness assessments", counts["assessments"]),
            ("With caveats", counts["with_caveats"]),
            ("Recorded caveats", counts["caveats"]),
            ("Blocking conditions", counts["blocking_conditions"]),
        ])
        if counts["caveats"] or counts["blocking_conditions"]:
            st.warning(
                "This history product completed with saved evidence limitations. "
                "Review its governed scope before interpreting movement.",
                icon=":material/warning:",
            )
        else:
            st.success(
                "No evidence-fitness limitations were recorded for this product.",
                icon=":material/check_circle:",
            )
        st.info(
            "Matching client identity and ordered observation dates do not by "
            "themselves prove unchanged portfolio scope, source mappings, or "
            "analytical rules.",
            icon=":material/info:",
        )


def _render_scope(product: dict[str, Any]) -> None:
    scope = st.expander(
        "Observation and snapshot scope",
        icon=":material/event_note:",
        on_change="rerun",
    )
    if scope.open:
        with scope:
            st.dataframe(
                history_scope_frame(product),
                hide_index=True,
                width="stretch",
            )
            st.caption(
                "Observation date is the business date represented by the "
                "evidence. Snapshot ID identifies the canonical observation."
            )


def _render_recorded_findings(catalogue, product: dict[str, Any]) -> None:
    findings, error = _recorded_findings(catalogue, product)
    st.subheader("Recorded historical findings", icon=":material/repeat:")
    st.caption(
        "Deterministic conditions saved by historical diagnosis. Significance "
        "and possible causes remain matters for interpretation."
    )
    if error:
        st.warning(
            f"Recorded historical findings are unavailable: {error}",
            icon=":material/warning:",
        )
    elif not findings:
        st.info("No historical findings were recorded for this product.")
    else:
        for finding in findings:
            render_finding(finding)


def _render_comparison(catalogue, comparisons: list[dict[str, Any]]) -> None:
    if not comparisons:
        st.info("No two-observation comparisons are available.")
        return

    choices = {
        history_product_label(item, "comparison_id"): item
        for item in comparisons
    }
    selected_label = st.selectbox(
        "Comparison",
        list(choices),
        help="A comparison contains exactly two governed observations.",
    )
    item = choices[selected_label]
    counts = history_fitness_counts(item)

    render_metric_row([
        MetricCard(
            "Observed changes",
            item.get("change_count", 0),
            icon=":material/difference:",
        ),
        MetricCard(
            "Historical findings",
            item.get("finding_count", 0),
            icon=":material/find_in_page:",
        ),
        MetricCard(
            "Compared observations",
            len(history_scope_frame(item)),
            icon=":material/event_repeat:",
        ),
        MetricCard(
            "Recorded caveats",
            counts["caveats"],
            icon=":material/warning:",
        ),
    ])
    _render_scope(item)

    findings_column, boundary_column = st.columns([1.55, 1], gap="medium")
    with findings_column:
        _render_recorded_findings(catalogue, item)
    with boundary_column:
        _render_comparability(item)

    with render_panel(
        "Governed change evidence",
        "Saved row-level changes between the selected observations.",
        icon=":material/table_view:",
    ):
        reference = item.get("detailed_output")
        if not reference:
            st.info("No detailed comparison evidence was recorded.")
            return
        try:
            changes = catalogue.read_table(governed_reference(reference))
            st.dataframe(changes, hide_index=True, width="stretch")
        except (FileNotFoundError, ValueError, MetadataReadError) as error:
            st.warning(
                f"Detailed comparison evidence is unavailable: {error}",
                icon=":material/warning:",
            )


def _render_trend(catalogue, trends: list[dict[str, Any]]) -> None:
    if not trends:
        st.info("No trend windows are available.")
        return

    choices = {
        history_product_label(item, "trend_id"): item for item in trends
    }
    selected_label = st.selectbox(
        "Trend window",
        list(choices),
        help="A trend includes every eligible observation between its endpoints.",
    )
    item = choices[selected_label]
    trend_id = str(item.get("trend_id", "trend"))
    counts = history_fitness_counts(item)

    render_metric_row([
        MetricCard(
            "Governed observations",
            item.get("observation_count", 0),
            icon=":material/event:",
        ),
        MetricCard(
            "Adjacent transitions",
            item.get("transition_count", 0),
            icon=":material/arrow_forward:",
        ),
        MetricCard(
            "Historical findings",
            item.get("finding_count", 0),
            icon=":material/find_in_page:",
        ),
        MetricCard(
            "Recorded caveats",
            counts["caveats"],
            icon=":material/warning:",
        ),
    ])
    _render_scope(item)
    st.warning(
        "Continuity policy: "
        + str(
            item.get(
                "continuity_policy",
                "Not recorded; review the governed trend evidence.",
            )
        ),
        icon=":material/link_off:",
    )

    references = item.get("detailed_outputs", {})
    tables: dict[str, Any] = {}
    table_errors = []
    for name, reference in references.items():
        try:
            tables[name] = catalogue.read_table(governed_reference(reference))
        except (FileNotFoundError, ValueError, MetadataReadError) as error:
            table_errors.append(str(error))

    observations = tables.get("project_observation_history")
    summary = tables.get("project_trend_summary")
    trajectory = None
    excluded = 0
    if observations is None or summary is None:
        st.warning(
            "Delivery trajectory is unavailable because the governed "
            "observation history or trend summary could not be read."
        )
    else:
        try:
            trajectory, excluded = prepare_delivery_trajectory(
                observations, summary
            )
            trajectory_metrics = delivery_trajectory_metrics(summary)
        except ValueError as error:
            st.warning(f"Delivery trajectory is unavailable: {error}")

    if trajectory is not None:
        st.subheader("Delivery trajectory", icon=":material/trending_up:")
        st.caption(
            "Forecast-finish movement and reported RAG across the selected "
            "governed observation window."
        )
        render_metric_row([
            ("Projects moved", trajectory_metrics["projects_moved"]),
            ("Moved later", trajectory_metrics["projects_slipped"]),
            ("Total days slipped", trajectory_metrics["total_days_slipped"]),
            ("RAG changes", trajectory_metrics["status_changes"]),
        ])

        if trajectory.empty:
            st.info(
                "No project observations have usable forecast finish dates "
                "for this trend window."
            )
        else:
            has_movers = bool(trajectory["HadFinishMovement"].any())
            scope = st.segmented_control(
                "Project scope",
                ["Forecast movers", "All projects"],
                default="Forecast movers" if has_movers else "All projects",
                required=True,
                key=f"history_scope_{trend_id}",
            )
            visible = scope_delivery_trajectory(
                trajectory, movers_only=scope == "Forecast movers"
            )
            chart_event = st.altair_chart(
                delivery_trajectory_chart(visible),
                width="stretch",
                key=f"history_trajectory_{trend_id}_{scope}",
                on_select="rerun",
                selection_mode="trajectory_pick",
            )
            st.caption(
                "Lines start again after a continuity break. Points show the "
                "reported RAG. Select a project to inspect it; double-click "
                "to clear the chart selection."
            )

            project_rows = (
                visible[["ProjectID", "DisplayName"]]
                .drop_duplicates(subset=["ProjectID"])
                .sort_values(["DisplayName", "ProjectID"])
            )
            project_labels = dict(
                project_rows[["ProjectID", "DisplayName"]].itertuples(
                    index=False, name=None
                )
            )
            project_key = f"history_project_{trend_id}_{scope}"
            chart_project_id = selected_trajectory_project_id(chart_event)
            if chart_project_id in project_labels:
                st.session_state[project_key] = chart_project_id
            if st.session_state.get(project_key) not in project_labels:
                st.session_state[project_key] = next(iter(project_labels), None)

            selected_project = st.selectbox(
                "Inspect project",
                list(project_labels),
                format_func=project_labels.get,
                key=project_key,
            )
            facts = delivery_project_facts(visible, selected_project)
            if facts:
                with render_panel(
                    f"{facts['project_name']} · {facts['project_id']}",
                    "Recorded movement within the latest continuous segment.",
                    icon=":material/account_tree:",
                ):
                    render_metric_row([
                        (
                            "Net forecast movement",
                            f"{facts['net_movement_days']:+d} days",
                        ),
                        ("Slippage transitions", facts["slippage_transitions"]),
                        (
                            "Latest forecast finish",
                            facts["latest_finish"].strftime("%d %b %Y"),
                        ),
                        ("Reported RAG", facts["status_path"]),
                    ])
                    if facts["unavailable_transitions"]:
                        st.warning(
                            f"{facts['unavailable_transitions']} adjacent "
                            "transition(s) were unavailable; the chart does "
                            "not bridge those gaps.",
                            icon=":material/link_off:",
                        )

    if excluded:
        st.warning(
            f"{excluded} observation row(s) were not plotted because "
            "identity, dates, or sequence were unusable."
        )
    if table_errors:
        st.warning(
            f"{len(table_errors)} governed trend artifact(s) could not be read."
        )

    findings_column, boundary_column = st.columns([1.55, 1], gap="medium")
    with findings_column:
        _render_recorded_findings(catalogue, item)
    with boundary_column:
        _render_comparability(item)

    if tables:
        evidence = st.expander(
            "Governed trend evidence",
            icon=":material/database:",
            on_change="rerun",
        )
        if evidence.open:
            with evidence:
                for name, table in tables.items():
                    st.markdown(f"**{name.replace('_', ' ').title()}**")
                    st.dataframe(table, hide_index=True, width="stretch")


_, catalogue, client_id, _ = console_context()

render_hero(
    "History",
    "History",
    "A change-over-time viewpoint over comparable observations and recurring "
    "delivery behaviour. Use it to distinguish observed movement from a "
    "consultant's interpretation of its significance.",
    icon=":material/timeline:",
)

comparisons = safe(lambda: catalogue.list_comparisons(client_id), []) if client_id else []
trends = safe(lambda: catalogue.list_trends(client_id), []) if client_id else []

if not comparisons and not trends:
    st.info(
        "No governed historical products are available for this client. "
        "Point-in-time diagnosis remains available without history.",
        icon=":material/history_toggle_off:",
    )
else:
    available_views = []
    if trends:
        available_views.append("Trend window")
    if comparisons:
        available_views.append("Two-observation comparison")
    view = st.segmented_control(
        "Historical view",
        available_views,
        default=available_views[0],
        required=True,
        key="history_view",
        persist_state="page",
        wrap=True,
    )
    if view == "Two-observation comparison":
        _render_comparison(catalogue, comparisons)
    else:
        _render_trend(catalogue, trends)
