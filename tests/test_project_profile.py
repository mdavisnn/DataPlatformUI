"""Tests for project-profile presentation models and charts."""

import pandas as pd

from components.project_profile import (
    attention_map_chart,
    project_fingerprint_chart,
)
from services.project_profile import (
    prepare_attention_map,
    prepare_project_fingerprint,
    selected_attention_project,
)


def profile_rows():
    common = {
        "ProjectName": "Alpha",
        "PopulationCount": 4,
        "Q1": 10,
        "Median": 25,
        "Q3": 50,
        "OutsideIqr": False,
        "Availability": "Available",
        "AvailabilityReason": "",
    }
    return pd.DataFrame([
        {
            **common, "ProjectID": "P1", "Domain": "Schedule",
            "MetricID": "schedule_condition_task_pct",
            "MetricLabel": "Tasks with schedule conditions",
            "Value": 50, "Unit": "%", "PercentileRank": 75,
        },
        {
            **common, "ProjectID": "P1", "Domain": "Resources",
            "MetricID": "conflict_resource_pct",
            "MetricLabel": "Resources with conflicts",
            "Value": 25, "Unit": "%", "PercentileRank": 50,
        },
        {
            **common, "ProjectID": "P1", "Domain": "Dependencies",
            "MetricID": "average_dependency_connectivity",
            "MetricLabel": "Average task connectivity",
            "Value": 2, "Unit": "connections", "PercentileRank": 100,
            "OutsideIqr": True,
        },
    ])


def health_rows():
    return pd.DataFrame([{
        "ProjectID": "P1", "ProjectName": "Alpha", "RAGStatus": "Amber",
        "DataFitness": "Fit", "FindingCount": 2, "HighFindings": 1,
        "MediumFindings": 1, "LowFindings": 0,
    }])


def test_attention_map_uses_governed_measures_and_serializes():
    attention = prepare_attention_map(profile_rows(), health_rows())

    row = attention.iloc[0]
    assert row["ScheduleConditionPct"] == 50
    assert row["ConflictResourcePct"] == 25
    assert row["FindingStatus"] == "Significant"
    assert bool(row["Plottable"])
    assert "layer" in attention_map_chart(attention).to_dict()


def test_fingerprint_formats_values_and_marks_unusual_context():
    fingerprint = prepare_project_fingerprint(profile_rows(), "P1")

    dependency = fingerprint[
        fingerprint["MetricID"] == "average_dependency_connectivity"
    ].iloc[0]
    assert dependency["ValueLabel"] == "2 connections"
    assert dependency["Unusual"] == "Outside IQR"
    assert "layer" in project_fingerprint_chart(fingerprint).to_dict()


def test_attention_map_keeps_projects_when_dependency_measure_is_unavailable():
    profile = profile_rows()
    dependency = profile["MetricID"].eq("average_dependency_connectivity")
    profile.loc[dependency, "Value"] = pd.NA
    profile.loc[dependency, "Median"] = pd.NA
    profile.loc[dependency, "Availability"] = "Not assessed"

    attention = prepare_attention_map(profile, health_rows())

    assert bool(attention.loc[0, "Plottable"])
    assert attention.loc[0, "DependencyEvidence"] == "Unavailable"


def test_attention_selection_reads_project_id():
    event = {"selection": {"project_select": [{"ProjectID": "P1"}]}}

    assert selected_attention_project(event) == "P1"
    assert selected_attention_project({"selection": {}}) is None
