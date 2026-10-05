"""Native Streamlit components for reviewing one governed Finding."""

from __future__ import annotations

from typing import Any

import streamlit as st

from components.console import render_metric_row, status_badge
from services.findings import (
    affected_entities_frame,
    capability_for_finding,
    filter_evidence_for_finding,
    finding_evidence_frame,
)
from services.platform_reader import MetadataReadError


def _render_rule_context(finding: dict[str, Any]) -> None:
    st.markdown("**Deterministic condition**")
    st.write(finding.get("description", "No description was recorded."))
    st.table(
        {
            ":material/rule: Rule": finding.get(
                "rule_id", "Not recorded"
            ),
            ":material/analytics: Diagnostic": finding.get(
                "diagnostic_id", "Not recorded"
            ),
        },
        border="horizontal",
        width="content",
    )
    evidence = finding_evidence_frame(finding)
    if evidence.empty:
        st.caption("No summary evidence measures were recorded.")
    else:
        st.dataframe(evidence, hide_index=True, width="stretch")
    st.info(
        "This is a deterministic finding, not an interpretation. It records "
        "that the evidence met the named rule; it does not claim why the "
        "condition exists.",
        icon=":material/info:",
    )


def _render_supporting_evidence(catalogue, finding: dict[str, Any]) -> None:
    references = finding.get("supporting_artifacts", [])
    if not references:
        st.caption("No supporting artifact references were recorded.")
        return

    for index, reference in enumerate(references, start=1):
        st.markdown(f"**Evidence source {index}**")
        st.caption(str(reference))
        try:
            evidence = catalogue.read_table(str(reference))
            matching = filter_evidence_for_finding(evidence, finding)
        except (FileNotFoundError, ValueError, MetadataReadError) as error:
            st.warning(
                f"Supporting evidence is unavailable: {error}",
                icon=":material/warning:",
            )
            continue
        if matching.empty:
            st.warning(
                "The linked artifact contains no rows for this Finding's "
                "recorded rule ID.",
                icon=":material/search_off:",
            )
            continue
        st.dataframe(
            matching,
            hide_index=True,
            width="stretch",
            height=min(420, 80 + len(matching) * 35),
        )


def _render_affected_entities(finding: dict[str, Any]) -> None:
    entities = affected_entities_frame(finding)
    if entities.empty:
        st.caption("No affected entity references were recorded.")
        return
    counts = (
        entities.groupby("Entity type")
        .size()
        .reset_index(name="Count")
        .sort_values("Count", ascending=False)
    )
    st.dataframe(counts, hide_index=True, width="stretch")
    st.dataframe(
        entities,
        hide_index=True,
        width="stretch",
        height=min(420, 80 + len(entities) * 35),
    )


def _render_fitness(
    finding: dict[str, Any], fitness: dict[str, Any],
) -> None:
    capability = capability_for_finding(finding)
    assessment = fitness.get("capabilities", {}).get(capability or "")
    if not assessment:
        st.caption(
            "No directly corresponding capability-fitness assessment was "
            "recorded for this Finding domain."
        )
        return

    st.markdown(status_badge(assessment.get("status")))
    st.caption(f"Capability: {capability.replace('_', ' ').title()}")
    render_metric_row([
        ("Blocking conditions", len(assessment.get("blocking_conditions", []))),
        ("Caveats", len(assessment.get("caveats", []))),
        ("Unavailable rules", len(assessment.get("unavailable_rules", []))),
    ])
    st.info(
        "Fitness describes whether the evidence could support this type of "
        "analysis. It is separate from the delivery condition recorded by "
        "the Finding.",
        icon=":material/fact_check:",
    )


def render_finding_detail(
    catalogue,
    finding: dict[str, Any],
    fitness: dict[str, Any],
) -> None:
    """Render one selected Finding with traceable supporting context."""

    st.markdown(status_badge(finding.get("severity")))
    st.subheader(finding.get("title", "Untitled finding"))
    st.caption(finding.get("finding_id", "Unknown Finding ID"))
    st.table(
        {
            "Domain": str(finding.get("domain", "unknown")).title(),
            "Rule": finding.get("rule_id", "Not recorded"),
            "Observation": finding.get("observation_date", "Not recorded"),
            "Snapshot": finding.get("snapshot_id", "Not recorded"),
        },
        border="horizontal",
        width="stretch",
    )

    detail_view = st.segmented_control(
        "Finding detail",
        [
            "Why it fired",
            "Evidence",
            "Affected entities",
            "Evidence fitness",
        ],
        default="Why it fired",
        key=f"finding_detail_{finding.get('finding_id', 'unknown')}",
        persist_state="page",
        wrap=True,
    )
    if detail_view == "Evidence":
        _render_supporting_evidence(catalogue, finding)
    elif detail_view == "Affected entities":
        _render_affected_entities(finding)
    elif detail_view == "Evidence fitness":
        _render_fitness(finding, fitness)
    else:
        _render_rule_context(finding)
