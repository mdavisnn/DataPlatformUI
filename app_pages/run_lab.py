"""Guided controls over DataPlatform's existing deterministic workflow."""

from datetime import date

import streamlit as st

from components.console import (
    MetricCard,
    render_hero,
    render_metric_row,
    render_panel,
)
from services.console_context import console_context, safe
from services.workflow import assess_evidence, diagnose_snapshot, inspect_evidence


def _stage_badge(label: str, ready: bool) -> None:
    st.badge(
        f"{label} · {'Ready' if ready else 'Waiting'}",
        icon=":material/check_circle:" if ready else ":material/hourglass_empty:",
        color="green" if ready else "gray",
    )


def _operation_result(result: dict) -> bool:
    succeeded = result["exit_code"] == 0
    st.code(result["output"] or "No command output was returned.")
    st.caption(f"Process exit code: {result['exit_code']}")
    return succeeded


settings, catalogue, client_id, _ = console_context()
runs = safe(lambda: catalogue.list_runs(client_id), []) if client_id else []
awaiting = [item for item in runs if item.get("status") == "awaiting_assessment"]
snapshots = safe(lambda: catalogue.list_snapshots(client_id), []) if client_id else []

render_hero(
    "Operate",
    "Run the lab",
    "An operational viewpoint over the evidence lifecycle from inspection to "
    "assessment and diagnosis. Use it to run the existing deterministic "
    "workflow with explicit human control and reproducible identifiers.",
    icon=":material/play_circle:",
)

st.warning(
    "Prototype control surface: use only with test or appropriately controlled evidence.",
    icon=":material/warning:",
)

render_metric_row([
    MetricCard(
        "Selected client",
        client_id or "None",
        icon=":material/business:",
    ),
    MetricCard(
        "Technical runs",
        len(runs),
        icon=":material/settings_suggest:",
    ),
    MetricCard(
        "Awaiting assessment",
        len(awaiting),
        icon=":material/pending_actions:",
    ),
    MetricCard(
        "Canonical observations",
        len(snapshots),
        icon=":material/photo_library:",
    ),
])

with st.container(
    border=True,
    horizontal=True,
    wrap=True,
    horizontal_alignment="distribute",
    vertical_alignment="center",
    gap="small",
):
    _stage_badge("1 · Inspect", bool(client_id))
    st.caption(":material/arrow_forward:")
    _stage_badge("2 · Assess", bool(awaiting))
    st.caption(":material/arrow_forward:")
    _stage_badge("3 · Diagnose", bool(snapshots))

with render_panel(
    "1 · Understand the evidence",
    "Discover and profile supported source files before any canonical observation exists.",
    icon=":material/search:",
):
    st.caption(
        "Raw inbox: "
        f"{settings.storage_root / 'raw' / str(client_id or '<select-client>')}"
    )
    st.info(
        "Inspection creates a technical run ID. It does not create a business "
        "observation or diagnose delivery performance.",
        icon=":material/info:",
    )
    if st.button(
        "Inspect raw evidence",
        type="primary",
        icon=":material/search:",
        disabled=not client_id,
    ):
        with st.status("Inspecting evidence…", expanded=True) as status:
            result = inspect_evidence(settings, client_id)
            succeeded = _operation_result(result)
            status.update(
                label="Inspection complete" if succeeded else "Inspection failed",
                state="complete" if succeeded else "error",
                expanded=not succeeded,
            )

with render_panel(
    "2 · Assess and canonicalise",
    "Assess one inspected run for an explicit business observation date.",
    icon=":material/fact_check:",
):
    if awaiting:
        st.badge(
            "Ready for assessment",
            icon=":material/check_circle:",
            color="green",
        )
        st.caption(
            f"{len(awaiting)} inspected run(s) are ready for assessment."
        )
    else:
        st.badge(
            "Waiting for an inspected run",
            icon=":material/hourglass_empty:",
            color="gray",
        )

    with st.form("assess-form", border=False):
        run_id = st.selectbox(
            "Technical run ID",
            [item["run_id"] for item in awaiting],
            disabled=not awaiting,
            help="Identifies when and how the source evidence was processed.",
        )
        observation_date = st.date_input(
            "Business observation date",
            value=date.today(),
            help="The date the source evidence describes, not the processing date.",
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
            succeeded = _operation_result(result)
            status.update(
                label="Assessment complete" if succeeded else "Assessment failed",
                state="complete" if succeeded else "error",
                expanded=not succeeded,
            )

with render_panel(
    "3 · Diagnose the observation",
    "Run deterministic diagnostic rules against one explicit canonical snapshot.",
    icon=":material/analytics:",
):
    if not snapshots:
        st.info(
            "Complete an assessment before running diagnosis.",
            icon=":material/info:",
        )
    else:
        options = {
            (
                f"{item.get('observation_date', 'Undated')} · "
                f"{item['snapshot_id']}"
            ): item["snapshot_id"]
            for item in snapshots
        }
        target = st.selectbox(
            "Canonical observation",
            list(options),
            key="diagnosis_snapshot",
            help=(
                "The snapshot ID identifies the immutable canonical observation "
                "used by diagnosis."
            ),
        )
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
        if not_fit:
            st.error(
                f"{len(not_fit)} capability assessment(s) are not fit. "
                "Diagnosis requires an explicit capability-scoped acknowledgement.",
                icon=":material/block:",
            )
        else:
            st.success(
                "No not-fit capability assessments require acknowledgement.",
                icon=":material/check_circle:",
            )
        overrides = st.pills(
            "Explicitly acknowledge not-fit capabilities",
            not_fit,
            selection_mode="multi",
            disabled=not not_fit,
            help=(
                "Only select a capability when you deliberately accept its "
                "evidence limitation."
            ),
        )
        if st.button("Run diagnosis", icon=":material/analytics:"):
            with st.status("Running diagnosis…", expanded=True) as status:
                result = diagnose_snapshot(
                    settings,
                    client_id,
                    options[target],
                    list(overrides or []),
                )
                succeeded = _operation_result(result)
                status.update(
                    label="Diagnosis complete" if succeeded else "Diagnosis failed",
                    state="complete" if succeeded else "error",
                    expanded=not succeeded,
                )

st.caption(
    "Run ID records technical processing. Observation date records when the "
    "evidence was true. Snapshot ID identifies the canonical observation."
)
