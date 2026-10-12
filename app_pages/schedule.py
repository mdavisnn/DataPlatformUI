"""Read-only DCMA 14-Point schedule assessment for one observation."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from components.console import render_hero, render_metric_row
from components.schedule_assessment import (
    assessment_matrix_chart,
    duration_distribution_chart,
)
from services.console_context import console_context
from services.lenses import diagnostic_outcome, product_reference
from services.platform_reader import MetadataReadError
from services.schedule_assessment import (
    filter_assessment,
    metric_labels,
    project_labels,
    status_date_source_label,
    status_label,
    supporting_conditions,
    truthy,
    unavailable_measures,
    validate_dcma_products,
)


STATUS_OPTIONS = {
    "Outside tripwire": "outside_threshold",
    "Within threshold": "within_threshold",
    "Not assessable": "not_assessable",
}


def _read_product(catalogue, outcome, name):
    reference = product_reference(outcome, name)
    if not reference:
        raise ValueError(f"DCMA schedule product {name!r} is not recorded")
    return catalogue.read_table(reference)


def _project_filter(
    label: str,
    labels: dict[str, str],
    *,
    key: str,
) -> str | None:
    project_ids = sorted(labels)
    return st.selectbox(
        label,
        [None, *project_ids],
        format_func=lambda value: (
            "All projects" if value is None else labels.get(value, value)
        ),
        key=key,
    )


def _overview_view(
    project_summary: pd.DataFrame,
    assessment: pd.DataFrame,
    labels: dict[str, str],
    snapshot_id: str,
) -> None:
    st.subheader("Portfolio assessment overview")
    st.caption(
        "Each cell is a backend-recorded project-metric result. Tripwires "
        "identify evidence for investigation; they do not form a composite "
        "schedule score or compliance determination."
    )
    selected_project = _project_filter(
        "Project",
        labels,
        key=f"schedule_overview_project_{snapshot_id}",
    )
    visible_assessment = filter_assessment(
        assessment, project_id=selected_project
    )
    visible_summary = project_summary.copy()
    if selected_project is not None:
        visible_summary = visible_summary[
            visible_summary["ProjectID"].astype(str) == selected_project
        ]

    if visible_assessment.empty:
        st.info("No DCMA assessment results match the selected project.")
    else:
        st.altair_chart(
            assessment_matrix_chart(visible_assessment),
            width="stretch",
        )

    st.subheader("Project assessment coverage")
    st.caption(
        "Assessed, outside-tripwire and unavailable results remain separate. "
        "Within assessed thresholds does not mean every metric was available."
    )
    display = visible_summary[[
        "ProjectName",
        "ProjectID",
        "AssessmentStatus",
        "TaskCount",
        "EligibleActivityCount",
        "AssessableMetrics",
        "OutOfThresholdMetrics",
        "NotAssessableMetrics",
    ]].rename(columns={
        "ProjectName": "Project",
        "ProjectID": "Project ID",
        "AssessmentStatus": "Assessment status",
        "TaskCount": "Activities",
        "EligibleActivityCount": "Eligible activities",
        "AssessableMetrics": "Assessed results",
        "OutOfThresholdMetrics": "Outside tripwire",
        "NotAssessableMetrics": "Not assessable",
    })
    st.dataframe(display, hide_index=True, width="stretch")


def _metric_detail_view(
    assessment: pd.DataFrame,
    conditions: pd.DataFrame,
    labels: dict[str, str],
    snapshot_id: str,
) -> None:
    st.subheader("Metric results and supporting evidence")
    st.caption(
        "Filter the governed results, then inspect the task or dependency "
        "conditions supporting the same project and metric."
    )
    metric_names = metric_labels(assessment)
    filter_columns = st.columns(2)
    selected_project = filter_columns[0].selectbox(
        "Project",
        [None, *sorted(labels)],
        format_func=lambda value: (
            "All projects" if value is None else labels.get(value, value)
        ),
        key=f"schedule_detail_project_{snapshot_id}",
    )
    selected_metric = filter_columns[1].selectbox(
        "DCMA metric",
        [None, *sorted(metric_names)],
        format_func=lambda value: (
            "All metrics" if value is None else metric_names.get(value, value)
        ),
        key=f"schedule_detail_metric_{snapshot_id}",
    )
    selected_status_labels = st.pills(
        "Recorded result",
        list(STATUS_OPTIONS),
        selection_mode="multi",
        key=f"schedule_detail_status_{snapshot_id}",
    )
    selected_statuses = [
        STATUS_OPTIONS[label] for label in selected_status_labels
    ]
    visible = filter_assessment(
        assessment,
        project_id=selected_project,
        metric_number=selected_metric,
        statuses=selected_statuses,
    )
    visible_conditions = supporting_conditions(conditions, visible)

    if visible.empty:
        st.info("No DCMA results match the selected filters.")
    else:
        results = visible.copy()
        results["Status"] = results["Status"].map(status_label)
        results["StatusDateSource"] = results["StatusDateSource"].map(
            status_date_source_label
        )
        results = results[[
            "ProjectName",
            "MetricNumber",
            "RuleID",
            "MetricName",
            "Status",
            "Value",
            "Unit",
            "Comparison",
            "Threshold",
            "EvidenceCoveragePct",
            "StatusDate",
            "StatusDateSource",
            "Population",
            "Reason",
        ]].rename(columns={
            "ProjectName": "Project",
            "MetricNumber": "No.",
            "RuleID": "Rule ID",
            "MetricName": "Metric",
            "Status": "Result",
            "Threshold": "Tripwire",
            "EvidenceCoveragePct": "Evidence coverage (%)",
            "StatusDate": "Status date",
            "StatusDateSource": "Status date source",
            "Population": "Population assessed",
            "Reason": "Limitation",
        })
        st.dataframe(results, hide_index=True, width="stretch")

    st.subheader("Supporting conditions")
    st.caption(
        "Conditions are factual evidence rows, not separate Findings and not "
        "explanations of why the schedule behaves this way."
    )
    if visible_conditions.empty:
        st.info("No supporting conditions exist for the visible results.")
    else:
        fields = [
            column for column in (
                "MetricNumber",
                "RuleID",
                "MetricName",
                "ProjectName",
                "EntityType",
                "EntityID",
                "TaskName",
                "DependencyID",
                "Condition",
                "ObservedValue",
                "Threshold",
                "Message",
            )
            if column in visible_conditions
        ]
        evidence = visible_conditions[fields].rename(columns={
            "MetricNumber": "No.",
            "RuleID": "Rule ID",
            "MetricName": "Metric",
            "ProjectName": "Project",
            "EntityType": "Entity type",
            "EntityID": "Entity ID",
            "TaskName": "Activity",
            "DependencyID": "Dependency ID",
            "ObservedValue": "Observed value",
            "Threshold": "Condition threshold",
            "Message": "Evidence statement",
        })
        st.dataframe(evidence, hide_index=True, width="stretch")


def _activity_evidence_view(
    project_summary: pd.DataFrame,
    activity_profile: pd.DataFrame,
    labels: dict[str, str],
    snapshot_id: str,
) -> None:
    st.subheader("Activity evidence")
    st.caption(
        "Inspect the saved duration, milestone, float and evidence-coverage "
        "measures behind the assessment."
    )
    selected_project = _project_filter(
        "Project",
        labels,
        key=f"schedule_activity_project_{snapshot_id}",
    )
    visible_activity = activity_profile.copy()
    visible_summary = project_summary.copy()
    if selected_project is not None:
        visible_activity = visible_activity[
            visible_activity["ProjectID"].astype(str) == selected_project
        ]
        visible_summary = visible_summary[
            visible_summary["ProjectID"].astype(str) == selected_project
        ]

    duration_basis = st.segmented_control(
        "Duration basis",
        ["Baseline working days", "Forecast calendar days"],
        default="Baseline working days",
        key=f"schedule_duration_basis_{snapshot_id}",
    )
    duration_column, duration_title = (
        (
            "BaselineDurationWorkingDays",
            "Baseline duration (Monday-Friday working days)",
        )
        if duration_basis == "Baseline working days"
        else ("ForecastDurationDays", "Forecast duration (calendar days)")
    )
    durations = visible_activity.copy()
    durations[duration_column] = pd.to_numeric(
        durations[duration_column], errors="coerce"
    )
    durations = durations.dropna(subset=[duration_column])
    if durations.empty:
        st.info("No saved activity durations are available in this scope.")
    else:
        st.altair_chart(
            duration_distribution_chart(
                durations, duration_column, duration_title
            ),
            width="stretch",
        )

    detail_columns = st.columns(2)
    with detail_columns[0]:
        st.subheader("Milestone position")
        milestones = visible_activity[
            truthy(visible_activity["IsMilestone"])
        ]
        milestone_fields = [
            column for column in (
                "ProjectName",
                "TaskName",
                "ForecastFinish",
                "ActualFinish",
                "Status",
                "TotalFloatDays",
                "MissingLogic",
                "HasNegativeFloat",
                "HasInvalidDate",
            )
            if column in milestones
        ]
        if milestones.empty:
            st.info("No milestone evidence is available in this scope.")
        else:
            milestone_display = milestones[milestone_fields].rename(columns={
                "ProjectName": "Project",
                "TaskName": "Milestone",
                "ForecastFinish": "Forecast finish",
                "ActualFinish": "Actual finish",
                "TotalFloatDays": "Total float (days)",
                "MissingLogic": "Missing logic",
                "HasNegativeFloat": "Negative float",
                "HasInvalidDate": "Invalid date",
            })
            st.dataframe(
                milestone_display,
                hide_index=True,
                width="stretch",
            )

    with detail_columns[1]:
        st.subheader("Schedule evidence coverage")
        coverage_fields = [
            column for column in (
                "ProjectName",
                "TaskCount",
                "EligibleActivityCount",
                "BaselineCoveragePct",
                "FloatCoveragePct",
                "CriticalEvidenceCoveragePct",
                "MedianBaselineDurationWorkingDays",
                "MaxBaselineDurationWorkingDays",
            )
            if column in visible_summary
        ]
        coverage = visible_summary[coverage_fields].rename(columns={
            "ProjectName": "Project",
            "TaskCount": "Activities",
            "EligibleActivityCount": "Eligible activities",
            "BaselineCoveragePct": "Baseline coverage (%)",
            "FloatCoveragePct": "Float coverage (%)",
            "CriticalEvidenceCoveragePct": "Criticality coverage (%)",
            "MedianBaselineDurationWorkingDays": (
                "Median baseline duration (working days)"
            ),
            "MaxBaselineDurationWorkingDays": (
                "Maximum baseline duration (working days)"
            ),
        })
        st.dataframe(
            coverage,
            hide_index=True,
            width="stretch",
        )


_, catalogue, client_id, snapshot = console_context()

render_hero(
    "Point-in-time diagnostic",
    "DCMA 14-Point schedule assessment",
    "Review project-level DCMA tripwires, metric availability and the governed "
    "activity or dependency evidence behind each recorded result.",
    icon=":material/calendar_month:",
)

if not snapshot:
    st.info("No diagnosed observation is available.")
    st.stop()

snapshot_id = snapshot["snapshot_id"]
bundle = catalogue.snapshot_bundle(snapshot_id, client_id)
outcome = diagnostic_outcome(bundle["diagnosis"], "schedule")
if (
    not outcome
    or outcome.get("status") != "success"
    or outcome.get("diagnostic_id") != "dcma_14_point"
):
    st.info(
        "The DCMA schedule assessment is unavailable for this observation. "
        "Run a current diagnosis or review its capability fitness."
    )
    st.stop()

try:
    project_summary = _read_product(catalogue, outcome, "project_summary")
    assessment = _read_product(catalogue, outcome, "assessment")
    conditions = _read_product(catalogue, outcome, "conditions")
    activity_profile = _read_product(catalogue, outcome, "activity_profile")
    validate_dcma_products(
        project_summary, assessment, conditions, activity_profile
    )
except (FileNotFoundError, ValueError, MetadataReadError) as error:
    st.warning(f"DCMA schedule evidence is unavailable: {error}")
    st.stop()

metrics = outcome.get("metrics", {})
render_metric_row([
    ("Projects assessed", metrics.get("projects_analysed")),
    ("Assessed results", metrics.get("metrics_assessed")),
    ("Outside tripwire", metrics.get("metrics_outside_threshold")),
    ("Not assessable", metrics.get("metrics_not_assessable")),
    ("Projects outside tripwire", metrics.get("projects_outside_threshold")),
])

limitations = unavailable_measures(metrics)
if not limitations.empty:
    st.info(
        f"{len(limitations)} DCMA metric(s) are unavailable across this "
        "observation. Their reasons remain visible in Assessment basis and "
        "limitations below.",
        icon=":material/info:",
    )

view = st.segmented_control(
    "Schedule assessment perspective",
    ["Portfolio overview", "Metric detail", "Activity evidence"],
    default="Portfolio overview",
    key=f"schedule_assessment_view_{snapshot_id}",
)
labels = project_labels(project_summary)
if view == "Metric detail":
    _metric_detail_view(
        assessment,
        conditions,
        labels,
        snapshot_id,
    )
elif view == "Activity evidence":
    _activity_evidence_view(
        project_summary,
        activity_profile,
        labels,
        snapshot_id,
    )
else:
    _overview_view(project_summary, assessment, labels, snapshot_id)

with st.expander("Assessment basis and limitations"):
    working_day_basis = metrics.get(
        "working_day_basis", "Not recorded"
    )
    st.write(
        "Working-day basis: "
        f"**{str(working_day_basis).replace('_', ' ')}**."
    )
    if limitations.empty:
        st.caption("No observation-wide unavailable DCMA metrics were recorded.")
    else:
        st.dataframe(limitations, hide_index=True, width="stretch")
    st.caption(
        "DCMA tripwires are deterministic investigation thresholds. They are "
        "not a composite health score, certification result or causal "
        "interpretation."
    )
