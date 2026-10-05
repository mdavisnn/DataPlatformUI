"""Configure, run and review deterministic SchedulePlatform scenarios."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from components.console import render_hero, render_metric_row
from components.scenario_charts import (
    scenario_project_timeline,
    scenario_resource_load_chart,
)
from services.console_context import console_context
from services.platform_reader import MetadataReadError
from services.scenario_planning import (
    ScenarioPlanningError,
    assignment_change_frame,
    build_configuration_document,
    candidate_summary_frame,
    default_project_policies,
    empty_substitutions,
    empty_targets,
    list_generation_packages,
    project_comparison_frame,
    resource_impact_summary,
    resource_load_comparison_frame,
    run_scenario_generation,
    schedule_platform_ready,
)


OBJECTIVE_LABELS = {
    "protect_priority": "Protect priority",
    "minimise_total_slippage": "Minimise total slippage",
    "minimise_changes": "Minimise changes",
}
ACTION_LABELS = {
    "move_task_dates": "Move task dates",
    "reassign_resource": "Reassign resource",
}


settings, catalogue, client_id, snapshot = console_context()

render_hero(
    "Deterministic planning",
    "Scenario planning",
    "A controlled what-if viewpoint over bounded schedule changes. Use it to "
    "compare feasible options against the immutable canonical baseline while "
    "keeping hypothetical plans separate from diagnostic findings.",
    icon=":material/event_repeat:",
)

if not snapshot or not client_id:
    st.info("Select an assessed observation before planning scenarios.")
    st.stop()

ready, readiness_message = schedule_platform_ready(settings)
if not ready:
    st.info(readiness_message, icon=":material/settings:")
    st.caption(
        "Scenario planning is optional; the rest of DataPlatformUI remains "
        "available without SchedulePlatform."
    )
    st.stop()

snapshot_id = str(snapshot["snapshot_id"])
st.caption(
    f"Source observation: {snapshot.get('observation_date', 'undated')} · "
    f"{client_id} · {snapshot_id}"
)
st.warning(
    "Generated scenarios are hypothetical SchedulePlatform artefacts. They "
    "do not modify the canonical observation, DataPlatform findings, or history.",
    icon=":material/info:",
)

try:
    projects = catalogue.read_snapshot_dataset(snapshot, "projects")
    tasks = catalogue.read_snapshot_dataset(snapshot, "tasks")
    resources = catalogue.read_snapshot_dataset(snapshot, "resources")
    assignments = catalogue.read_snapshot_dataset(snapshot, "assignments")
except (FileNotFoundError, ValueError, MetadataReadError) as error:
    st.warning(
        "This observation cannot support scenario planning because its "
        f"canonical schedule evidence is unavailable: {error}"
    )
    st.stop()

try:
    policy_defaults = default_project_policies(projects)
except ScenarioPlanningError as error:
    st.warning(str(error))
    st.stop()

task_ids = sorted(
    tasks.get("TaskID", pd.Series(dtype="string"))
    .dropna().astype(str).unique().tolist()
)
resource_ids = sorted(
    resources.get("ResourceID", pd.Series(dtype="string"))
    .dropna().astype(str).unique().tolist()
)
resource_names = {
    str(row["ResourceID"]): str(row["ResourceName"])
    for _, row in resources.dropna(subset=["ResourceID"]).iterrows()
    if "ResourceName" in resources.columns
    and pd.notna(row.get("ResourceName"))
}
project_ids = sorted(
    projects.get("ProjectID", pd.Series(dtype="string"))
    .dropna().astype(str).unique().tolist()
)
entity_ids = sorted(set(project_ids) | set(task_ids))

packages = list_generation_packages(settings, client_id, snapshot_id)
active_run_key = f"scenario_active_run_{snapshot_id}"
config_expander_key = f"scenario_configuration_open_{snapshot_id}"
collapse_request_key = f"scenario_configuration_collapse_{snapshot_id}"
success_message_key = f"scenario_generation_success_{snapshot_id}"
if st.session_state.pop(collapse_request_key, False):
    st.session_state[config_expander_key] = False

objective_key = f"scenario_objective_{snapshot_id}"
scenario_count_key = f"scenario_count_{snapshot_id}"
actions_key = f"scenario_actions_{snapshot_id}"
summary_objective = OBJECTIVE_LABELS.get(
    st.session_state.get(objective_key, "protect_priority"),
    "Protect priority",
)
summary_count = st.session_state.get(scenario_count_key, 3)
summary_actions = st.session_state.get(
    actions_key, list(ACTION_LABELS.values())
)
config_panel = st.expander(
    f"Planning configuration · {summary_objective} · "
    f"{summary_count} options · {len(summary_actions or [])} actions",
    expanded=not bool(packages),
    key=config_expander_key,
    icon=":material/tune:",
    on_change="rerun",
)
config_panel.caption(
    "All fields become a strict SchedulePlatform V1 JSON configuration and "
    "are validated again by the scheduling engine."
)

with config_panel.form(f"scenario_configuration_{snapshot_id}", border=False):
    settings_columns = st.columns(4)
    objective = settings_columns[0].selectbox(
        "Ranking objective",
        list(OBJECTIVE_LABELS),
        format_func=OBJECTIVE_LABELS.get,
        key=objective_key,
    )
    scenario_count = settings_columns[1].number_input(
        "Options to return",
        min_value=1,
        max_value=20,
        value=3,
        step=1,
        key=scenario_count_key,
    )
    candidate_limit = settings_columns[2].number_input(
        "Candidate limit",
        min_value=1,
        max_value=10000,
        value=100,
        step=10,
        key=f"scenario_candidate_limit_{snapshot_id}",
    )
    max_action_depth = settings_columns[3].number_input(
        "Maximum action depth",
        min_value=1,
        max_value=20,
        value=4,
        step=1,
        key=f"scenario_action_depth_{snapshot_id}",
    )

    selected_action_labels = st.pills(
        "Permitted replanning actions",
        list(ACTION_LABELS.values()),
        default=list(ACTION_LABELS.values()),
        selection_mode="multi",
        key=actions_key,
    )
    allowed_actions = [
        key
        for key, label in ACTION_LABELS.items()
        if label in (selected_action_labels or [])
    ]
    assignment_fallback = st.checkbox(
        "Allow missing assignment dates to fall back to task forecast dates",
        value=False,
        key=f"scenario_assignment_fallback_{snapshot_id}",
        help=(
            "This is an explicit analytical assumption. The generated result "
            "records every assignment that uses the fallback."
        ),
    )

    st.markdown("#### Project priorities and movement limits")
    st.caption(
        "Priority 1 is highest. Protected project dates cannot be moved "
        "automatically; flexible projects may move only within their limit."
    )
    project_policies = st.data_editor(
        policy_defaults,
        hide_index=True,
        disabled=["ProjectID", "ProjectName"],
        width="stretch",
        key=f"scenario_project_policies_{snapshot_id}",
        column_config={
            "ProjectID": st.column_config.TextColumn("Project ID"),
            "ProjectName": st.column_config.TextColumn("Project"),
            "Protection": st.column_config.SelectboxColumn(
                "Protection",
                options=["protected", "flexible"],
                required=True,
            ),
            "Priority": st.column_config.NumberColumn(
                "Priority", min_value=1, max_value=3, step=1, required=True
            ),
            "Max movement (days)": st.column_config.NumberColumn(
                "Max finish movement (calendar days)",
                min_value=0,
                step=1,
                required=True,
            ),
        },
    )

    with st.container(border=True):
        st.markdown("#### Permitted resource substitutions")
        st.caption(
            "Each row authorises one complete assignment substitution. "
            "Role or team similarity does not grant permission."
        )
        resource_substitutions = st.data_editor(
            empty_substitutions(),
            hide_index=True,
            num_rows="dynamic",
            width="stretch",
            key=f"scenario_substitutions_{snapshot_id}",
            column_config={
                "TaskID": st.column_config.SelectboxColumn(
                    "Task", options=task_ids, required=True
                ),
                "FromResourceID": st.column_config.SelectboxColumn(
                    "From resource", options=resource_ids, required=True
                ),
                "ToResourceID": st.column_config.SelectboxColumn(
                    "To resource", options=resource_ids, required=True
                ),
            },
        )

    with st.container(border=True):
        st.markdown("#### Schedule targets")
        st.caption(
            "Report-only targets show attainment without affecting ranking. "
            "A missed hard target makes a candidate infeasible."
        )
        targets = st.data_editor(
            empty_targets(),
            hide_index=True,
            num_rows="dynamic",
            width="stretch",
            key=f"scenario_targets_{snapshot_id}",
            column_config={
                "TargetID": st.column_config.TextColumn(
                    "Target ID", required=True
                ),
                "Type": st.column_config.SelectboxColumn(
                    "Type",
                    options=["project_finish", "task_finish"],
                    required=True,
                ),
                "EntityID": st.column_config.SelectboxColumn(
                    "Project or task", options=entity_ids, required=True
                ),
                "TargetDate": st.column_config.DateColumn(
                    "Target date", required=True
                ),
                "Treatment": st.column_config.SelectboxColumn(
                    "Treatment",
                    options=["report_only", "hard_constraint"],
                    required=True,
                ),
            },
        )

    submitted = st.form_submit_button(
        "Generate deterministic scenarios",
        type="primary",
        icon=":material/play_arrow:",
    )

generated_package = None
if submitted:
    try:
        configuration = build_configuration_document(
            settings,
            client_id=client_id,
            snapshot_id=snapshot_id,
            objective=objective,
            scenario_count=int(scenario_count),
            candidate_limit=int(candidate_limit),
            max_action_depth=int(max_action_depth),
            allowed_actions=allowed_actions,
            allow_assignment_date_fallback=assignment_fallback,
            project_policies=project_policies,
            resource_substitutions=resource_substitutions,
            targets=targets,
        )
        with st.status(
            "Generating bounded deterministic scenarios…",
            expanded=True,
        ) as status:
            generated_package = run_scenario_generation(
                settings, configuration
            )
            status.update(
                label="Scenario generation complete",
                state="complete",
            )
        st.success(
            "The run was saved as an isolated SchedulePlatform result package."
        )
        generated_id = generated_package["run"].get("run_id")
        st.session_state[active_run_key] = generated_id
        st.session_state[collapse_request_key] = True
        st.session_state[success_message_key] = (
            "Scenario generation complete. Planning configuration was "
            "collapsed so the ranked results are immediately visible."
        )
        st.rerun()
    except ScenarioPlanningError as error:
        st.error(str(error), icon=":material/error:")

if success_message := st.session_state.pop(success_message_key, None):
    st.success(success_message)

if not packages:
    st.info(
        "No deterministic scenario run has been saved for this observation."
    )
    st.stop()

run_by_id = {
    str(package["run"]["run_id"]): package for package in packages
}
if st.session_state.get(active_run_key) not in run_by_id:
    st.session_state[active_run_key] = next(iter(run_by_id))
selected_run_id = st.selectbox(
    "Saved scenario run",
    list(run_by_id),
    key=active_run_key,
    format_func=lambda run_id: (
        f"{run_by_id[run_id]['run'].get('completed_at', 'Undated')} · "
        f"{run_id}"
    ),
)
package = run_by_id[selected_run_id]
run = package["run"]
generation = package["generation"]

st.divider()
st.subheader("Generation outcome")
render_metric_row([
    ("Status", str(generation.get("status", "unknown")).replace("_", " ").title()),
    ("Selected options", len(generation.get("selected_candidates", []))),
    ("Candidates evaluated", generation.get("candidates_evaluated")),
    ("States deduplicated", generation.get("states_deduplicated")),
    ("Search truncated", "Yes" if generation.get("search_truncated") else "No"),
])

for warning in generation.get("warnings", []):
    st.warning(
        warning.get("message", "SchedulePlatform recorded a warning."),
        icon=":material/warning:",
    )

baseline = generation.get("baseline", {})
fitness_conditions = baseline.get("input_fitness", {}).get("conditions", [])
observed_conditions = baseline.get("observed_conditions", [])
with st.container(border=True):
    st.subheader("Immutable baseline")
    st.caption(
        "Baseline conditions describe the imported observation. They are "
        "kept separate from generated-scenario feasibility."
    )
    render_metric_row([
        ("Baseline status", str(baseline.get("status", "unknown")).title()),
        ("Observed conditions", len(observed_conditions)),
        ("Fitness conditions", len(fitness_conditions)),
        ("Engine", baseline.get("engine_version")),
        ("Rules", baseline.get("rule_set_version")),
    ])
    if observed_conditions:
        st.dataframe(
            pd.DataFrame(observed_conditions)[["code", "message"]],
            hide_index=True,
            width="stretch",
        )
    if fitness_conditions:
        with st.expander(
            f"Input fitness conditions ({len(fitness_conditions)})"
        ):
            st.dataframe(
                pd.DataFrame(fitness_conditions)[
                    ["severity", "condition_id", "blocking", "message"]
                ],
                hide_index=True,
                width="stretch",
            )

selected_candidates = generation.get("selected_candidates", [])
if not selected_candidates:
    st.info(
        "No generated scenario was selected. Review the status, baseline "
        "conditions, configured permissions, and search bounds."
    )
    evaluated = generation.get("evaluated_candidates", [])
    violations = [
        {
            "Proposal": candidate.get("proposal", {}).get("proposal_id"),
            "Feasibility": candidate.get("result", {}).get(
                "feasibility_status"
            ),
            "Code": violation.get("code"),
            "Message": violation.get("message"),
        }
        for candidate in evaluated
        for violation in candidate.get("result", {}).get(
            "constraint_violations", []
        )
    ]
    if violations:
        st.dataframe(
            pd.DataFrame(violations), hide_index=True, width="stretch"
        )
    st.stop()

st.subheader("Ranked feasible options")
summary = candidate_summary_frame(generation)
st.dataframe(summary, hide_index=True, width="stretch")

candidate_by_id = {
    str(item["proposal"]["proposal_id"]): item
    for item in selected_candidates
}
selected_proposal_id = st.selectbox(
    "Inspect option",
    list(candidate_by_id),
    key=f"scenario_candidate_{selected_run_id}",
    format_func=lambda proposal_id: (
        f"Option {list(candidate_by_id).index(proposal_id) + 1} · "
        f"{proposal_id}"
    ),
)
candidate = candidate_by_id[selected_proposal_id]
proposal = candidate["proposal"]
result = candidate["result"]
impact = resource_impact_summary(generation, candidate)

st.markdown("#### Selected option impact")
st.write(proposal.get("rationale", "No rationale was recorded."))
render_metric_row([
    (
        "Over-capacity intervals",
        f"{impact['baseline_over_capacity_intervals']} → "
        f"{impact['scenario_over_capacity_intervals']}",
    ),
    (
        "Peak affected-resource load",
        f"{impact['baseline_peak_affected_load']:.0f}% → "
        f"{impact['scenario_peak_affected_load']:.0f}%",
    ),
    ("Affected resources", impact["affected_resources"]),
    ("Changed assignments", impact["changed_assignments"]),
    (
        "Maximum finish movement",
        f"{impact['maximum_finish_movement_days']} days",
    ),
])

view = st.segmented_control(
    "Result view",
    ["Resource impact", "Timeline impact", "Actions & targets", "Evidence"],
    default="Resource impact",
    key=f"scenario_result_view_v2_{selected_run_id}",
)

if view == "Resource impact":
    load_comparison = resource_load_comparison_frame(
        generation, candidate
    )
    if load_comparison.empty:
        st.info(
            "This option does not change a resource assignment or the "
            "calculated resource-load profile."
        )
    else:
        load_comparison["Resource"] = load_comparison["ResourceID"].map(
            lambda resource_id: (
                f"{resource_names[resource_id]} · {resource_id}"
                if resource_id in resource_names
                else resource_id
            )
        )
        st.caption(
            "Baseline load is dashed grey, scenario load is solid blue, "
            "and the dashed red line is recorded capacity. Red points mark "
            "over-capacity intervals. The chart focuses on changed periods."
        )
        st.altair_chart(
            scenario_resource_load_chart(load_comparison),
            width="stretch",
        )

    assignment_changes = assignment_change_frame(candidate)
    st.markdown("#### Changed assignments")
    if assignment_changes.empty:
        st.caption("No assignment resource or date changes were recorded.")
    else:
        assignment_changes = assignment_changes.copy()
        for column in ("Baseline resource", "Scenario resource"):
            assignment_changes[column] = assignment_changes[column].map(
                lambda resource_id: (
                    f"{resource_names[resource_id]} · {resource_id}"
                    if resource_id in resource_names
                    else resource_id
                )
            )
        st.dataframe(
            assignment_changes,
            hide_index=True,
            width="stretch",
            column_config={
                column: st.column_config.DatetimeColumn(
                    column, format="DD MMM YYYY"
                )
                for column in (
                    "Baseline start",
                    "Baseline finish",
                    "Scenario start",
                    "Scenario finish",
                )
            },
        )

elif view == "Timeline impact":
    comparison = project_comparison_frame(generation, candidate)
    if comparison.empty:
        st.info("No comparable project schedule rows are available.")
    else:
        movement_table = (
            comparison.loc[
                comparison["Schedule"] == "Scenario",
                [
                    "ProjectID",
                    "ProjectName",
                    "Start",
                    "Finish",
                    "Finish movement (days)",
                ],
            ]
            .sort_values(["Finish movement (days)", "ProjectID"])
            .reset_index(drop=True)
        )
        moved_projects = movement_table.loc[
            movement_table["Finish movement (days)"].fillna(0) != 0,
            "ProjectID",
        ].tolist()
        if moved_projects:
            st.altair_chart(
                scenario_project_timeline(
                    comparison.loc[
                        comparison["ProjectID"].isin(moved_projects)
                    ]
                ),
                width="stretch",
            )
            st.dataframe(
                movement_table.loc[
                    movement_table["ProjectID"].isin(moved_projects)
                ],
                hide_index=True,
                width="stretch",
                column_config={
                    "Start": st.column_config.DatetimeColumn(
                        "Scenario start", format="DD MMM YYYY"
                    ),
                    "Finish": st.column_config.DatetimeColumn(
                        "Scenario finish", format="DD MMM YYYY"
                    ),
                },
            )
        else:
            st.success(
                "This option leaves all calculated project finish dates "
                "unchanged."
            )

    changed_dates = [
        item for item in result.get("date_deltas", [])
        if item.get("origin") != "unchanged"
    ]
    if changed_dates:
        st.markdown("#### Direct and propagated date changes")
        st.dataframe(
            pd.DataFrame(changed_dates),
            hide_index=True,
            width="stretch",
        )

elif view == "Actions & targets":
    task_changes = proposal.get("task_date_changes", [])
    reassignments = proposal.get("resource_reassignments", [])
    action_columns = st.columns(2)
    with action_columns[0]:
        st.markdown("#### Task date changes")
        if task_changes:
            st.dataframe(
                pd.DataFrame(task_changes),
                hide_index=True,
                width="stretch",
            )
        else:
            st.caption("No direct task date changes.")
    with action_columns[1]:
        st.markdown("#### Resource reassignments")
        if reassignments:
            st.dataframe(
                pd.DataFrame(reassignments),
                hide_index=True,
                width="stretch",
            )
        else:
            st.caption("No direct resource reassignments.")

    target_outcomes = candidate.get("target_outcomes", [])
    if target_outcomes:
        st.markdown("#### Target outcomes")
        st.dataframe(
            pd.DataFrame(target_outcomes),
            hide_index=True,
            width="stretch",
        )

else:
    violations = result.get("constraint_violations", [])
    if violations:
        st.markdown("#### Constraint evidence")
        st.dataframe(
            pd.DataFrame(violations)[["code", "message"]],
            hide_index=True,
            width="stretch",
        )
    else:
        st.success(
            "The scheduling engine recorded no constraint violations for "
            "this feasible option."
        )
    st.markdown("#### Run provenance")
    st.json({
        "run_id": run.get("run_id"),
        "client_id": run.get("client_id"),
        "snapshot_id": run.get("snapshot_id"),
        "generation_id": run.get("generation_id"),
        "configuration_fingerprint": run.get(
            "configuration_fingerprint"
        ),
        "objective": run.get("objective"),
        "engine_version": run.get("engine_version"),
        "rule_set_version": run.get("rule_set_version"),
        "result_package": str(package["root"]),
    })
    with st.expander("Validated V1 configuration"):
        st.json(package["configuration"])
