import pandas as pd
import pytest

from services.schedule_assessment import (
    filter_assessment,
    status_date_source_label,
    supporting_conditions,
    unavailable_measures,
    validate_dcma_products,
)


def _assessment():
    return pd.DataFrame([
        {
            "ProjectID": "P1",
            "ProjectName": "Alpha",
            "MetricNumber": 1,
            "RuleID": "DCMA-01-LOGIC",
            "MetricName": "Logic",
            "Status": "outside_threshold",
            "Value": 100,
            "Unit": "%",
            "Comparison": "maximum",
            "Threshold": 5,
            "EvidenceCoveragePct": 100,
            "StatusDate": "2026-09-01",
            "StatusDateSource": "project_data_date",
            "Population": "eligible activities",
            "Reason": "",
            "WorkingDayBasis": "monday_friday_no_holidays",
        },
        {
            "ProjectID": "P2",
            "ProjectName": "Beta",
            "MetricNumber": 1,
            "RuleID": "DCMA-01-LOGIC",
            "MetricName": "Logic",
            "Status": "within_threshold",
            "Value": 0,
            "Unit": "%",
            "Comparison": "maximum",
            "Threshold": 5,
            "EvidenceCoveragePct": 100,
            "StatusDate": "2026-09-01",
            "StatusDateSource": "snapshot_observation_date",
            "Population": "eligible activities",
            "Reason": "",
            "WorkingDayBasis": "monday_friday_no_holidays",
        },
    ])


def test_filter_assessment_and_conditions_share_project_rule_scope():
    assessment = _assessment()
    conditions = pd.DataFrame([
        {
            "RuleID": "DCMA-01-LOGIC",
            "MetricNumber": 1,
            "MetricName": "Logic",
            "ProjectID": "P1",
            "ProjectName": "Alpha",
            "EntityType": "task",
            "EntityID": "T1",
            "Condition": "missing_logic",
            "ObservedValue": "successor",
            "Threshold": 5,
            "Message": "Missing successor logic",
        },
        {
            "RuleID": "DCMA-01-LOGIC",
            "MetricNumber": 1,
            "MetricName": "Logic",
            "ProjectID": "P2",
            "ProjectName": "Beta",
            "EntityType": "task",
            "EntityID": "T2",
            "Condition": "missing_logic",
            "ObservedValue": "predecessor",
            "Threshold": 5,
            "Message": "Not in the selected scope",
        },
    ])

    visible = filter_assessment(
        assessment,
        project_id="P1",
        statuses=["outside_threshold"],
    )
    evidence = supporting_conditions(conditions, visible)

    assert visible["ProjectID"].tolist() == ["P1"]
    assert evidence["EntityID"].tolist() == ["T1"]


def test_validate_products_exposes_missing_contract_columns():
    summary = pd.DataFrame(columns=[
        "ProjectID", "ProjectName", "TaskCount", "EligibleActivityCount",
        "AssessableMetrics", "OutOfThresholdMetrics",
        "NotAssessableMetrics", "AssessmentStatus",
    ])
    conditions = pd.DataFrame(columns=[
        "RuleID", "MetricNumber", "MetricName", "ProjectID", "ProjectName",
        "EntityType", "EntityID", "Condition", "ObservedValue", "Threshold",
        "Message",
    ])
    activities = pd.DataFrame(columns=[
        "ProjectID", "ProjectName", "TaskID", "TaskName",
        "BaselineDurationWorkingDays", "ForecastDurationDays", "IsMilestone",
    ])

    with pytest.raises(ValueError, match="WorkingDayBasis"):
        validate_dcma_products(
            summary,
            _assessment().drop(columns="WorkingDayBasis"),
            conditions,
            activities,
        )


def test_unavailable_measures_preserve_backend_reasons():
    result = unavailable_measures({
        "unavailable_measures": [{
            "rule_id": "DCMA-12-CRITICAL-PATH-TEST",
            "metric_name": "Critical Path Test",
            "reasons": ["Network recalculation is unavailable"],
        }]
    })

    assert result.to_dict("records") == [{
        "Metric": "Critical Path Test",
        "Rule ID": "DCMA-12-CRITICAL-PATH-TEST",
        "Reason": "Network recalculation is unavailable",
    }]
    assert status_date_source_label("snapshot_observation_date") == (
        "Observation date fallback"
    )
