"""Compact editable assumptions for the scenario discussion workspace."""

from datetime import date

import streamlit as st

from components.scenario_charts import planning_horizon_chart
from services.scenario_presentation import (
    OBJECTIVE_HELP, OBJECTIVE_LABELS, draft_from_planning, planning_from_editors,
)
from services.scenario_planning import empty_targets


ACTION_LABELS = {
    "move_task_dates": "Move task dates",
    "reassign_resource": "Reassign resource",
}


def render_scenario_configuration(
    prefix, projects, task_names, resource_names, project_names,
    observed_start, observed_finish, *, ready,
):
    """Keep editor inputs stable while saving the live draft separately."""
    draft_key = f"{prefix}_draft"
    draft = st.session_state[draft_key]
    seed_key = f"{prefix}_editor_seed"
    if seed_key not in st.session_state:
        st.session_state[seed_key] = draft_from_planning(draft, projects)
    seed = st.session_state[seed_key]
    revision = st.session_state.get(f"{prefix}_editor_revision", 0)
    for field in (
        "objective", "scenario_count", "allowed_actions", "candidate_limit",
        "max_action_depth", "allow_assignment_date_fallback",
    ):
        st.session_state.setdefault(f"{prefix}_{field}", draft[field])
    for field, saved in (("horizon_start", "start_date"), ("horizon_end", "end_date")):
        st.session_state.setdefault(
            f"{prefix}_{field}", (
                date.fromisoformat(draft["planning_horizon"][saved])
                if draft["planning_horizon"][saved] else None
            ),
        )
    selected_objective = st.segmented_control(
        "What matters most?", list(OBJECTIVE_LABELS), format_func=OBJECTIVE_LABELS.get,
        key=f"{prefix}_objective",
    )
    objective = selected_objective or draft["objective"]
    if selected_objective is None:
        st.caption("Choose what matters most before generating options.")
    st.caption(OBJECTIVE_HELP[objective])
    columns = st.columns(3)
    count = columns[0].number_input("Options to return", min_value=1, step=1, key=f"{prefix}_scenario_count")
    start = columns[1].date_input("Horizon start", key=f"{prefix}_horizon_start")
    finish = columns[2].date_input("Horizon end", key=f"{prefix}_horizon_end")
    st.caption(
        f"The observed baseline spans {observed_start:%d %b %Y} to {observed_finish:%d %b %Y}. "
        "The horizon includes both dates; extend it explicitly to allow later work."
    )
    valid_horizon = bool(start and finish and start <= observed_start <= observed_finish <= finish)
    if not valid_horizon:
        st.error("The planning horizon must contain the complete observed schedule.")
    if start and finish and finish >= start:
        st.altair_chart(
            planning_horizon_chart(observed_start, observed_finish, start, finish),
            width="stretch", alt="Planning horizon compared with the observed schedule",
        )
    actions = st.pills(
        "What may change?", list(ACTION_LABELS), format_func=ACTION_LABELS.get,
        selection_mode="multi", key=f"{prefix}_allowed_actions",
    ) or []
    st.caption("Protect a project's dates or allow movement within its limit. Priority 1 is highest.")
    policies = st.data_editor(
        seed["policies"], hide_index=True, disabled=["ProjectID", "ProjectName"],
        key=f"{prefix}_policies_{revision}", width="stretch",
        alt="Project priorities, protected dates and movement limits",
        column_config={
            "ProjectID": None,
            "ProjectName": st.column_config.TextColumn("Project", pinned=True),
            "Protection": st.column_config.SelectboxColumn(
                "Dates", options=["protected", "flexible"], required=True,
                format_func=lambda value: {"protected": "Keep fixed", "flexible": "May move"}.get(value, value),
            ),
            "Priority": st.column_config.NumberColumn("Priority", min_value=1, max_value=3, step=1, required=True),
            "Max movement (days)": st.column_config.NumberColumn(
                "Maximum finish movement (calendar days)", min_value=0, step=1, required=True,
            ),
        },
    )
    # Optional editors are visible only on demand. Their latest values are kept
    # as separate seeds before unmounting, rather than feeding edits back in.
    show_boundaries = st.toggle("Resource substitutions and target dates", key=f"{prefix}_boundaries")
    substitutions = seed["substitutions"]
    targets = seed["targets"]
    if not show_boundaries and st.session_state.get(f"{prefix}_boundaries_were_open"):
        substitutions, targets = st.session_state[f"{prefix}_boundary_values"]
    if show_boundaries:
        st.markdown("#### Authorised resource substitutions")
        st.caption("Each row permits one complete assignment substitution; matching role or team alone does not grant permission.")
        substitutions = st.data_editor(
            seed["substitutions"], num_rows="dynamic", hide_index=True, width="stretch",
            key=f"{prefix}_substitutions_{revision}", alt="Explicit resource substitution permissions",
            column_config={
                "TaskID": st.column_config.SelectboxColumn(
                    "Task", options=sorted(task_names), required=True,
                    format_func=lambda value: f"{task_names.get(value, value)} · {value}",
                ),
                "FromResourceID": st.column_config.SelectboxColumn(
                    "From resource", options=sorted(resource_names), required=True,
                    format_func=lambda value: f"{resource_names.get(value, value)} · {value}",
                ),
                "ToResourceID": st.column_config.SelectboxColumn(
                    "To resource", options=sorted(resource_names), required=True,
                    format_func=lambda value: f"{resource_names.get(value, value)} · {value}",
                ),
            },
        )
        entity_names = {**project_names, **task_names}
        st.markdown("#### Dates to track")
        st.caption("Track a finish date, or require candidates to finish by it.")
        targets = st.data_editor(
            seed["targets"] if not seed["targets"].empty else empty_targets(),
            num_rows="dynamic", hide_index=True, width="stretch",
            key=f"{prefix}_targets_{revision}", alt="Target dates and required finish dates",
            column_config={
                "TargetID": st.column_config.TextColumn("Target name", required=True),
                "Type": st.column_config.SelectboxColumn(
                    "Applies to", options=["project_finish", "task_finish"], required=True,
                    format_func=lambda value: {"project_finish": "Project finish", "task_finish": "Task finish"}.get(value, value),
                ),
                "EntityID": st.column_config.SelectboxColumn(
                    "Project or task", options=sorted(entity_names), required=True,
                    format_func=lambda value: f"{entity_names.get(value, value)} · {value}",
                ),
                "TargetDate": st.column_config.DateColumn("Finish by", required=True),
                "Treatment": st.column_config.SelectboxColumn(
                    "Treatment", options=["report_only", "hard_constraint"], required=True,
                    format_func=lambda value: {"report_only": "Track this date", "hard_constraint": "Must finish by this date"}.get(value, value),
                ),
            },
        )
    candidate_limit = draft["candidate_limit"]
    depth = draft["max_action_depth"]
    fallback = draft["allow_assignment_date_fallback"]
    if st.toggle("Advanced settings", key=f"{prefix}_advanced"):
        columns = st.columns(2)
        candidate_limit = columns[0].number_input("Candidate limit", min_value=1, step=10, key=f"{prefix}_candidate_limit")
        depth = columns[1].number_input("Maximum action depth", min_value=1, step=1, key=f"{prefix}_max_action_depth")
        fallback = st.checkbox("Use task forecast dates when assignment dates are missing", key=f"{prefix}_allow_assignment_date_fallback")
        st.caption("Execution backend: bounded deterministic search. CP-SAT awaits its public execution and persisted-provenance contracts.")
    current = planning_from_editors({
        "objective": objective, "scenario_count": int(count),
        "planning_horizon": {
            "start_date": start.isoformat() if start else None,
            "end_date": finish.isoformat() if finish else None,
        },
        "allowed_actions": actions, "candidate_limit": int(candidate_limit),
        "max_action_depth": int(depth), "allow_assignment_date_fallback": fallback,
    }, policies, substitutions, targets)
    st.session_state[draft_key] = current
    # Snapshot optional editors only while hiding them; on next mount a fresh
    # widget key ensures old row deltas cannot be applied twice.
    if not show_boundaries and st.session_state.pop(f"{prefix}_boundaries_were_open", False):
        st.session_state[seed_key] = draft_from_planning(current, projects)
        st.session_state[f"{prefix}_editor_revision"] = revision + 1
    if show_boundaries:
        st.session_state[f"{prefix}_boundary_values"] = (substitutions.copy(), targets.copy())
        st.session_state[f"{prefix}_boundaries_were_open"] = True
    if not actions:
        st.caption("Permit at least one replanning action to generate options.")
    submitted = st.button(
        "Generate options", type="primary", icon=":material/play_arrow:",
        disabled=not ready or not valid_horizon or not actions or selected_objective is None,
        key=f"{prefix}_generate",
    )
    return submitted, current, policies, substitutions, targets
