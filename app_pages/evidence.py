"""Evidence and capability-fitness view."""

import pandas as pd
import streamlit as st

from components.console import render_hero, render_metric_row, status_badge
from services.catalog import flatten_fitness
from services.console_context import console_context


_, catalogue, snapshot = console_context()

render_hero(
    "Understand & assess",
    "Can this evidence support the analysis?",
    "Fitness is assessed separately for each diagnostic capability; limitations remain visible beside the results.",
    icon=":material/fact_check:",
)

if not snapshot:
    st.info("No assessed observation is available.")
    st.stop()

bundle = catalogue.snapshot_bundle(snapshot["snapshot_id"])
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

st.dataframe(frame, hide_index=True)
capabilities = bundle["fitness"].get("capabilities", {})
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
                ("Unavailable rules", "unavailable_rules"),
            ):
                st.markdown(f"**{heading}**")
                items = assessment.get(key, [])
                if items:
                    st.dataframe(pd.DataFrame(items), hide_index=True)
                else:
                    st.caption("None recorded.")
