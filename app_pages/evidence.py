"""Evidence and capability-fitness view."""

import pandas as pd
import streamlit as st

from components.console import render_hero, render_metric_row, status_badge
from services.catalog import flatten_fitness
from services.console_context import console_context
from services.fitness import (
    capability_condition_frame,
    missing_dataset_frame,
    unavailable_rule_frame,
)
from services.platform_reader import MetadataReadError


_, catalogue, client_id, snapshot = console_context()

render_hero(
    "Understand & assess",
    "Can this evidence support the analysis?",
    "Fitness is assessed separately for each diagnostic capability; "
    "limitations remain visible beside the results.",
    icon=":material/fact_check:",
)

if not snapshot:
    st.info("No assessed observation is available.")
    st.stop()

bundle = catalogue.snapshot_bundle(snapshot["snapshot_id"], client_id)
manifest = bundle["snapshot"]
render_metric_row([
    ("Source files", len(manifest.get("source_files", []))),
    ("Canonical datasets", len(manifest.get("datasets", {}))),
    ("Observation date", manifest.get("observation_date", "—")),
])

st.subheader("Fitness by capability")
frame = flatten_fitness(bundle["fitness"])
if frame.empty:
    st.info("Fitness has not been assessed for this observation.")
    st.stop()

st.dataframe(frame, hide_index=True, width="stretch")
capabilities = bundle["fitness"].get("capabilities", {})
evidence_reference = bundle["fitness"].get("evidence_object")
try:
    evidence = (
        catalogue.read_table(evidence_reference)
        if evidence_reference else pd.DataFrame()
    )
except (FileNotFoundError, ValueError, MetadataReadError):
    evidence = pd.DataFrame()
for capability, assessment in capabilities.items():
    label = assessment.get("status", "unknown").replace("_", " ").title()
    details = st.expander(
        f"{capability.title()} · {label}",
        icon=":material/rule:",
        on_change="rerun",
    )
    if details.open:
        with details:
            st.markdown(status_badge(assessment.get("status")))
            for heading, key in (
                ("Blocking conditions", "blocking_conditions"),
                ("Caveats", "caveats"),
            ):
                st.markdown(f"**{heading}**")
                detail_frame = capability_condition_frame(
                    assessment, key, evidence
                )
                if not detail_frame.empty:
                    st.dataframe(
                        detail_frame,
                        hide_index=True,
                        width="stretch",
                    )
                else:
                    st.caption("None recorded.")
            st.markdown("**Missing datasets**")
            missing = missing_dataset_frame(assessment)
            if missing.empty:
                st.caption("None recorded.")
            else:
                st.dataframe(missing, hide_index=True, width="stretch")
            st.markdown("**Unavailable analyses**")
            unavailable = unavailable_rule_frame(assessment)
            if unavailable.empty:
                st.caption("None recorded.")
            else:
                st.dataframe(
                    unavailable,
                    hide_index=True,
                    width="stretch",
                )
