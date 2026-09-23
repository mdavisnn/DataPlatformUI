"""Guided controls over DataPlatform's existing deterministic workflow."""

from datetime import date

import streamlit as st

from components.console import render_hero
from services.console_context import console_context, safe
from services.workflow import assess_evidence, diagnose_snapshot, inspect_evidence


settings, catalogue, client_id, _ = console_context()

render_hero(
    "Guided operation",
    "Run the lab without the command line",
    "Each action calls the existing deterministic workflow. The console does not replace or reinterpret platform controls.",
    icon=":material/play_circle:",
)
st.warning(
    "Prototype control surface: use only with test or appropriately controlled evidence.",
    icon=":material/warning:",
)

st.subheader("1 · Understand the evidence")
st.caption(
    "Inspects supported files in the client raw inbox at "
    f"{settings.storage_root / 'raw' / str(client_id or '<select-client>')}."
)
if st.button(
    "Inspect raw evidence",
    type="primary",
    icon=":material/search:",
    disabled=not client_id,
):
    with st.status("Inspecting evidence…", expanded=True) as status:
        result = inspect_evidence(settings, client_id)
        st.code(result["output"] or "No command output was returned.")
        succeeded = result["exit_code"] == 0
        status.update(
            label="Inspection complete" if succeeded else "Inspection failed",
            state="complete" if succeeded else "error",
        )

st.subheader("2 · Assess and canonicalise")
runs = (
    safe(lambda: catalogue.list_runs(client_id), [])
    if client_id else []
)
awaiting = [item for item in runs if item.get("status") == "awaiting_assessment"]
with st.form("assess-form"):
    run_id = st.selectbox(
        "Inspected run",
        [item["run_id"] for item in awaiting],
        disabled=not awaiting,
    )
    observation_date = st.date_input(
        "Business observation date", value=date.today()
    )
    submitted = st.form_submit_button(
        "Assess evidence",
        disabled=not awaiting,
        icon=":material/fact_check:",
    )
if not awaiting:
    st.caption("No inspected runs are awaiting assessment.")
if submitted:
    with st.status("Assessing evidence…", expanded=True) as status:
        result = assess_evidence(
            settings,
            client_id,
            run_id,
            observation_date,
        )
        st.code(result["output"] or "No command output was returned.")
        succeeded = result["exit_code"] == 0
        status.update(
            label="Assessment complete" if succeeded else "Assessment failed",
            state="complete" if succeeded else "error",
        )

st.subheader("3 · Diagnose")
snapshots = (
    safe(lambda: catalogue.list_snapshots(client_id), [])
    if client_id else []
)
if not snapshots:
    st.info("Complete an assessment before running diagnosis.")
    st.stop()

options = {
    f"{item.get('observation_date', 'Undated')} · {item['snapshot_id']}": item["snapshot_id"]
    for item in snapshots
}
target = st.selectbox("Canonical observation", list(options), key="diagnosis_snapshot")
fitness = safe(
    lambda: catalogue.snapshot_bundle(
        options[target],
        client_id,
    )["fitness"],
    {},
)
not_fit = [
    name
    for name, value in fitness.get("capabilities", {}).items()
    if value.get("status") == "not_fit"
]
overrides = st.pills(
    "Explicitly acknowledge not-fit capabilities",
    not_fit,
    selection_mode="multi",
    disabled=not not_fit,
    help="Only select a capability when you deliberately accept its evidence limitation.",
)
if st.button("Run diagnosis", icon=":material/analytics:"):
    with st.status("Running diagnosis…", expanded=True) as status:
        result = diagnose_snapshot(
            settings,
            client_id,
            options[target],
            list(overrides or []),
        )
        st.code(result["output"] or "No command output was returned.")
        succeeded = result["exit_code"] == 0
        status.update(
            label="Diagnosis complete" if succeeded else "Diagnosis failed",
            state="complete" if succeeded else "error",
        )
