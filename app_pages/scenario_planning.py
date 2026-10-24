"""Explore saved schedule options with a client and adjust planning assumptions."""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from components.console import render_hero, render_metric_row
from components.scenario_configuration import render_scenario_configuration
from components.scenario_charts import (
    project_finish_movement_chart, scenario_project_timeline, scenario_resource_load_chart,
)
from services.console_context import console_context
from services.platform_reader import MetadataReadError
from services.scenario_planning import (
    ScenarioPlanningError, assignment_change_frame, build_configuration_document,
    candidate_summary_frame, constraint_violation_frame, default_project_policies,
    empty_substitutions, empty_targets, list_generation_packages, observed_schedule_bounds,
    project_comparison_frame, resource_load_comparison_frame, run_scenario_generation,
    schedule_platform_ready,
)
from services.scenario_presentation import (
    OBJECTIVE_LABELS, draft_from_planning, finish_movement_frame, generation_guidance,
    option_label, option_story, planning_from_editors, planning_signature,
)


settings, catalogue, client_id, snapshot = console_context()
render_hero(
    "Scenarios", "What could improve the plan?",
    "Compare bounded, feasible schedule options, understand what improves "
    "and discuss the changes each option requires.",
    icon=":material/event_repeat:",
)
if not snapshot or not client_id:
    st.info("Select an assessed observation before planning scenarios.")
    st.stop()

snapshot_id = str(snapshot["snapshot_id"])
prefix = f"scenario_{client_id}_{snapshot_id}"
st.caption(
    f"Source observation: {snapshot.get('observation_date', 'undated')} · "
    f"{client_id} · {snapshot_id}. Hypothetical options; source evidence stays unchanged."
)
try:
    projects = catalogue.read_snapshot_dataset(snapshot, "projects")
    tasks = catalogue.read_snapshot_dataset(snapshot, "tasks")
    resources = catalogue.read_snapshot_dataset(snapshot, "resources")
    assignments = catalogue.read_snapshot_dataset(snapshot, "assignments")
    observed_start, observed_finish = observed_schedule_bounds(projects, tasks, assignments)
    policies = default_project_policies(projects)
except (FileNotFoundError, ValueError, MetadataReadError, ScenarioPlanningError) as error:
    st.warning(f"Canonical schedule evidence is unavailable: {error}")
    st.stop()

task_names = {
    str(row["TaskID"]): str(row.get("TaskName") or row["TaskID"])
    for row in tasks.fillna("").to_dict("records")
}
resource_names = {
    str(row["ResourceID"]): str(row.get("ResourceName") or row["ResourceID"])
    for row in resources.fillna("").to_dict("records")
}
project_names = dict(zip(policies["ProjectID"], policies["ProjectName"]))
entity_names = {**project_names, **task_names}
packages = list_generation_packages(settings, client_id, snapshot_id)
run_by_id = {str(item["run"]["run_id"]): item for item in packages}
active_run_key = f"{prefix}_active_run"
config_key = f"{prefix}_configuration_open"
draft_key = f"{prefix}_draft"
seed_key = f"{prefix}_editor_seed"
revision_key = f"{prefix}_editor_revision"
if pending_run := st.session_state.pop(f"{prefix}_pending_run", None):
    st.session_state[active_run_key] = pending_run
if st.session_state.pop(f"{prefix}_collapse_configuration", False):
    st.session_state[config_key] = False

package = None
if run_by_id:
    if st.session_state.get(active_run_key) not in run_by_id:
        st.session_state[active_run_key] = next(iter(run_by_id))
    selected_run_id = st.selectbox(
        "Saved scenario run", list(run_by_id), key=active_run_key,
        format_func=lambda identifier: (
            f"{OBJECTIVE_LABELS.get(run_by_id[identifier]['configuration'].get('planning', {}).get('objective'), 'Saved options')}"
            f" · {run_by_id[identifier]['run'].get('completed_at', 'Undated')} · {identifier}"
        ),
    )
    package = run_by_id[selected_run_id]

default_planning = planning_from_editors({
    "objective": "protect_priority",
    "planning_horizon": {
        "start_date": observed_start.isoformat(), "end_date": observed_finish.isoformat(),
    },
    "scenario_count": 3, "candidate_limit": 100, "max_action_depth": 4,
    "allowed_actions": ["move_task_dates", "reassign_resource"],
    "allow_assignment_date_fallback": False,
}, policies, empty_substitutions(), empty_targets())
st.session_state.setdefault(draft_key, default_planning)
st.session_state.setdefault(revision_key, 0)
if package:
    planning = package["configuration"]["planning"]
    horizon = planning.get("planning_horizon", {})
    protected = sum(item.get("protection") == "protected" for item in planning.get("projects", []))
    st.write(f"Goal: {OBJECTIVE_LABELS.get(planning.get('objective'), 'Saved objective')}")
    st.caption(
        f"Saved boundaries: {protected} protected project(s) · "
        f"{horizon.get('start_date', 'Unknown')} to {horizon.get('end_date', 'Unknown')} · "
        f"{len(planning.get('resource_substitutions', []))} authorised substitution(s)"
    )
    if st.button(
        "Use these assumptions for a new run", key=f"{prefix}_reuse",
        icon=":material/content_copy:",
        help="Restore this run's goal, horizon, project policies, substitutions, targets and advanced settings.",
    ):
        restored = {**default_planning, **planning}
        st.session_state[draft_key] = restored
        st.session_state[seed_key] = draft_from_planning(restored, projects)
        st.session_state[revision_key] += 1
        for field in (
            "objective", "scenario_count", "candidate_limit", "max_action_depth",
            "allowed_actions", "allow_assignment_date_fallback",
        ):
            st.session_state[f"{prefix}_{field}"] = restored[field]
        for field, saved in (("horizon_start", "start_date"), ("horizon_end", "end_date")):
            st.session_state[f"{prefix}_{field}"] = date.fromisoformat(restored["planning_horizon"][saved])
        st.session_state.pop(f"{prefix}_boundary_values", None)
        st.session_state.pop(f"{prefix}_boundaries_were_open", None)
        st.session_state[config_key] = True

panel = st.expander(
    "Adjust assumptions", expanded=not bool(package), key=config_key,
    icon=":material/tune:", on_change="rerun",
)
submitted = False
if panel.open:
    with panel:
        ready, readiness_message = schedule_platform_ready(settings)
        if not ready:
            st.info("Generation needs its SchedulePlatform environment. Saved runs remain available.")
            st.caption(readiness_message)
        submitted, draft, project_policies, substitutions, targets = render_scenario_configuration(
            prefix, projects, task_names, resource_names, project_names,
            observed_start, observed_finish, ready=ready,
        )
    st.session_state[f"{prefix}_configuration_was_open"] = True
    st.session_state[f"{prefix}_draft_reviewed"] = True
elif st.session_state.pop(f"{prefix}_configuration_was_open", False):
    st.session_state[seed_key] = draft_from_planning(st.session_state[draft_key], projects)
    st.session_state[revision_key] += 1
    st.session_state.pop(f"{prefix}_boundaries_were_open", None)
    st.session_state.pop(f"{prefix}_boundary_values", None)

if package and st.session_state.get(f"{prefix}_draft_reviewed"):
    if planning_signature(st.session_state[draft_key]) != planning_signature(package["configuration"]["planning"]):
        st.warning(
            "Draft assumptions differ from the saved run shown below. "
            "Generate options to see results for the edited assumptions."
        )
    elif panel.open:
        st.caption("Draft assumptions match the saved run shown below.")

if submitted:
    try:
        configuration = build_configuration_document(
            settings, client_id=client_id, snapshot_id=snapshot_id,
            objective=draft["objective"],
            planning_horizon_start=draft["planning_horizon"]["start_date"],
            planning_horizon_end=draft["planning_horizon"]["end_date"],
            observed_schedule_start=observed_start, observed_schedule_end=observed_finish,
            scenario_count=draft["scenario_count"], candidate_limit=draft["candidate_limit"],
            max_action_depth=draft["max_action_depth"], allowed_actions=draft["allowed_actions"],
            allow_assignment_date_fallback=draft["allow_assignment_date_fallback"],
            project_policies=project_policies, resource_substitutions=substitutions, targets=targets,
        )
        with st.status("Exploring feasible schedule options…", expanded=True) as status:
            generated = run_scenario_generation(settings, configuration)
            status.update(label="Options saved", state="complete")
        st.session_state[f"{prefix}_pending_run"] = generated["run"]["run_id"]
        st.session_state[f"{prefix}_collapse_configuration"] = True
        st.session_state[f"{prefix}_generation_success"] = True
        st.rerun()
    except ScenarioPlanningError as error:
        st.error(str(error), icon=":material/error:")
if st.session_state.pop(f"{prefix}_generation_success", False):
    st.success("New results are saved. Compare the benefits and trade-offs below.")
if package is None:
    st.info("Choose your goal and boundaries, then generate options to discuss.")
    st.stop()

run = package["run"]
configuration = package["configuration"]
planning = configuration["planning"]
generation = package["generation"]
selected_candidates = generation.get("selected_candidates", [])
violation_summary = constraint_violation_frame(generation)
headline, guidance = generation_guidance(generation)
st.subheader(headline)
if generation.get("search_truncated"):
    st.warning(guidance)
else:
    st.caption(guidance)
for warning in generation.get("warnings", []):
    st.warning(warning.get("message", "The engine recorded a warning."))
if not violation_summary.loc[violation_summary["Code"] == "PLANNING-HORIZON-EXCEEDED"].empty:
    st.warning(
        "Some explored candidates exceeded the configured planning horizon. "
        "Review their evidence below and consider extending the horizon in Adjust assumptions."
    )

if selected_candidates:
    candidate_by_id = {item["proposal"]["proposal_id"]: item for item in selected_candidates}
    selected_key = f"{prefix}_{selected_run_id}_selected_option"
    if st.session_state.get(selected_key) not in candidate_by_id:
        st.session_state[selected_key] = next(iter(candidate_by_id))
    stories = [option_story(generation, item, planning, task_names, resource_names) for item in selected_candidates]
    for offset in range(0, len(selected_candidates), 3):
        columns = st.columns(min(3, len(selected_candidates) - offset))
        for index, column in enumerate(columns, start=offset):
            identifier = selected_candidates[index]["proposal"]["proposal_id"]
            story = stories[index]
            with column.container(border=True, height="stretch"):
                st.markdown(f"#### {option_label(index)}")
                st.caption("Highest-ranked option found" if index == 0 else f"Engine rank {index + 1}")
                for label, field in (("What improves", "benefit"), ("What changes", "changes"), ("Trade-off", "trade_off")):
                    st.markdown(f"**{label}**")
                    st.write(story[field])
                st.space("stretch")
                if st.button(
                    f"Inspect {option_label(index)}", key=f"{prefix}_{selected_run_id}_option_{index}",
                    type="primary" if st.session_state[selected_key] == identifier else "secondary",
                    width="stretch",
                ):
                    st.session_state[selected_key] = identifier
                    st.rerun()
    selected_index = list(candidate_by_id).index(st.session_state[selected_key])
    candidate = selected_candidates[selected_index]
    result = candidate["result"]
    story = stories[selected_index]
    st.subheader(f"{option_label(selected_index)} · what this means")
    st.write(f"{story['benefit']} {story['trade_off']}")
    st.caption(story["protection"])
    if story["actions"]:
        st.write(" ".join(story["actions"][:3]))
        if len(story["actions"]) > 3:
            st.caption("More actions are listed in Changes & targets.")
    render_metric_row([
        ("Overloaded resource-days", (
            f"{story['baseline_overload_days']} → {story['scenario_overload_days']}"
            if story["baseline_overload_days"] is not None and story["scenario_overload_days"] is not None
            else "Not recorded"
        )),
        ("Projects finishing later", story["delayed_projects"] if story["delayed_projects"] is not None else "Not recorded"),
        ("Tasks affected", story["tasks_changed"]),
    ])
    st.caption("One overloaded resource-day is one resource over its recorded capacity for one calendar day.")
    view = st.segmented_control(
        "Explore the impact", ["Resource load", "Finish dates", "Changes & targets"],
        default="Resource load", key=f"{prefix}_{selected_run_id}_view",
    )
    if view == "Resource load":
        load = resource_load_comparison_frame(generation, candidate)
        if load.empty:
            st.info("This option leaves the load profile unchanged, or no comparable resource evidence was saved.")
        else:
            load["Resource"] = load["ResourceID"].map(lambda value: f"{resource_names.get(value, value)} · {value}")
            st.caption("Dashed grey: baseline. Solid blue: option. Dashed red: capacity. Red points: overload.")
            st.altair_chart(scenario_resource_load_chart(load), width="stretch", alt="Baseline and option resource load against recorded capacity")
    elif view == "Finish dates":
        finishes = finish_movement_frame(generation, candidate, planning)
        if finishes.empty:
            st.info("No comparable project finish-date evidence was saved.")
        else:
            st.caption("Grey circles: baseline. Blue diamonds: option. Protected and unchanged projects remain visible.")
            plottable = finishes.dropna(subset=["Baseline finish", "Scenario finish"])
            if not plottable.empty:
                st.altair_chart(project_finish_movement_chart(plottable), width="stretch", alt="Project finish-date movements including protected projects")
            st.dataframe(finishes, hide_index=True, width="stretch", alt="Project finish dates and protection")
    else:
        st.markdown("#### Actions required")
        moves = candidate["proposal"].get("task_date_changes", [])
        reassignments = candidate["proposal"].get("resource_reassignments", [])
        rows = [{"Task": task_names.get(item["task_id"], item["task_id"]), **item} for item in [*moves, *reassignments]]
        if rows:
            frame = pd.DataFrame(rows)
            for field in ("from_resource_id", "to_resource_id"):
                if field in frame:
                    frame[field] = frame[field].map(lambda value: resource_names.get(value, value))
            st.dataframe(frame, hide_index=True, width="stretch", alt="Direct task moves and resource substitutions")
        else:
            st.caption("No direct task moves or resource substitutions.")
        if candidate.get("target_outcomes"):
            outcomes = pd.DataFrame(candidate["target_outcomes"])
            outcomes["Entity"] = outcomes["entity_id"].map(lambda value: entity_names.get(value, value))
            st.markdown("#### Dates to track")
            st.dataframe(outcomes, hide_index=True, width="stretch", alt="Target dates and recorded attainment")
        else:
            st.caption("No target dates were configured for this run.")
    details = st.expander("Detailed changes and option comparison", key=f"{prefix}_changes", on_change="rerun")
    if details.open:
        with details:
            st.caption("Engine ranking is preserved. Resource-load interval counts depend on interval boundaries.")
            st.dataframe(candidate_summary_frame(generation), hide_index=True, width="stretch", alt="Detailed ranked option comparison")
            changes = assignment_change_frame(candidate)
            if not changes.empty:
                changes["Task"] = changes["Task"].map(lambda value: task_names.get(value, value))
                for field in ("Baseline resource", "Scenario resource"):
                    changes[field] = changes[field].map(lambda value: resource_names.get(value, value))
                st.dataframe(changes, hide_index=True, width="stretch", alt="Changed assignment dates and resources")
            dates = [item for item in result.get("date_deltas", []) if item.get("origin") != "unchanged"]
            if dates:
                st.dataframe(pd.DataFrame(dates), hide_index=True, width="stretch", alt="Direct and propagated date changes")
            comparison = project_comparison_frame(generation, candidate)
            if not comparison.empty:
                st.altair_chart(scenario_project_timeline(comparison), width="stretch", alt="Complete baseline and scenario project schedules")
elif not violation_summary.empty:
    st.markdown("#### Recorded blockers")
    blockers = violation_summary.groupby(["Code", "Message"], dropna=False).size().reset_index(name="Occurrences")
    st.dataframe(blockers, hide_index=True, width="stretch", alt="Constraints blocking explored candidates")

evidence = st.expander(
    "Assumptions and run evidence", key=f"{prefix}_evidence",
    icon=":material/fact_check:", on_change="rerun",
)
if evidence.open:
    with evidence:
        st.subheader("Saved run details")
        horizon = planning.get("planning_horizon", {})
        render_metric_row([
            ("Config version", configuration.get("config_version")),
            ("Planning horizon", f"{horizon.get('start_date')} → {horizon.get('end_date')}"),
            ("Generation method", "Bounded deterministic search"),
        ])
        render_metric_row([
            ("Candidate limit", planning.get("candidate_limit")),
            ("Action depth", planning.get("max_action_depth")),
            ("Engine", run.get("engine_version")), ("Rules", run.get("rule_set_version")),
        ])
        st.caption(f"Configuration fingerprint: {run.get('configuration_fingerprint', 'Not recorded')}")
        st.json({
            **run, "config_version": configuration.get("config_version"),
            "planning_horizon": horizon, "generation_method": "bounded_deterministic_search",
            "result_package": str(package["root"]),
        })
        render_metric_row([
            ("Candidates evaluated", generation.get("candidates_evaluated")),
            ("States deduplicated", generation.get("states_deduplicated")),
            ("Search truncated", "Yes" if generation.get("search_truncated") else "No"),
        ])
        st.markdown("#### Immutable baseline")
        baseline = generation.get("baseline", {})
        st.caption(f"Recorded baseline status: {baseline.get('status', 'unknown')}")
        for title, rows in (
            ("Observed baseline conditions", baseline.get("observed_conditions", [])),
            ("Input-fitness conditions", baseline.get("input_fitness", {}).get("conditions", [])),
            ("Baseline assumptions", baseline.get("assumptions", [])),
        ):
            st.markdown(f"**{title}**")
            if rows:
                st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", alt=title)
            else:
                st.caption("None recorded.")
        if selected_candidates:
            st.markdown("#### Selected option validation")
            st.json({field: result.get(field, []) for field in (
                "feasibility_status", "constraint_violations", "warnings", "assumptions", "objective_metrics",
            )})
        if not violation_summary.empty:
            st.dataframe(violation_summary, hide_index=True, width="stretch", alt="All explored candidate constraint evidence")
        st.markdown("#### Validated V1.1 configuration")
        st.json(configuration)
