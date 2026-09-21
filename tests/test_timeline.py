import pandas as pd

from components.timeline import portfolio_timeline_chart
from services.timeline import (
    build_finding_occurrences,
    build_project_finding_occurrences,
    findings_for_project,
    findings_for_projects,
    portfolio_groups,
    prepare_portfolio_schedule,
    prepare_project_schedule,
    project_ids_for_portfolio,
    selected_finding_id,
    selected_project_id,
)


def schedule_rows():
    return pd.DataFrame([
        {
            "TaskID": "T1",
            "ProjectID": "P1",
            "WBS": "1",
            "TaskName": "Design",
            "IsMilestone": False,
            "ForecastStartDate": "2026-01-01",
            "ForecastFinishDate": "2026-01-31",
            "Status": "In Progress",
        },
        {
            "TaskID": "T2",
            "ProjectID": "P1",
            "WBS": "2",
            "TaskName": "Approval",
            "IsMilestone": True,
            "ForecastStartDate": "2026-02-01",
            "ForecastFinishDate": "2026-02-01",
            "Status": "Not Started",
        },
        {
            "TaskID": "T3",
            "ProjectID": "P1",
            "WBS": "3",
            "TaskName": "Invalid",
            "ForecastStartDate": "2026-03-10",
            "ForecastFinishDate": "2026-03-01",
        },
        {
            "TaskID": "T4",
            "ProjectID": "P2",
            "WBS": "1",
            "TaskName": "Other project",
            "ForecastStartDate": "2026-01-01",
            "ForecastFinishDate": "2026-01-10",
        },
    ])


def project_rows():
    return pd.DataFrame([
        {
            "ProjectID": "P1",
            "ProjectName": "Alpha",
            "PortfolioID": "PORT-A",
            "ForecastStartDate": "2026-01-01",
            "ForecastFinishDate": "2026-03-31",
            "LifecycleStatus": "Delivery",
            "RAGStatus": "Amber",
        },
        {
            "ProjectID": "P2",
            "ProjectName": "Beta",
            "PortfolioID": "PORT-B",
            "ForecastStartDate": "2026-02-01",
            "ForecastFinishDate": "2026-04-30",
        },
        {
            "ProjectID": "P3",
            "ProjectName": "Unassigned project",
            "PortfolioID": None,
            "ForecastStartDate": "2026-03-01",
            "ForecastFinishDate": "2026-03-15",
        },
        {
            "ProjectID": "P4",
            "ProjectName": "Invalid project",
            "PortfolioID": "PORT-A",
            "ForecastStartDate": "2026-05-10",
            "ForecastFinishDate": "2026-05-01",
        },
    ])


def test_prepare_portfolio_schedule_groups_filters_and_exposes_invalid_rows():
    assert portfolio_groups(project_rows()) == [
        "PORT-A",
        "PORT-B",
        "Unassigned",
    ]
    assert project_ids_for_portfolio(project_rows(), "PORT-A") == [
        "P1",
        "P4",
    ]

    schedule, excluded = prepare_portfolio_schedule(
        project_rows(),
        "PORT-A",
    )

    assert schedule["ProjectID"].tolist() == ["P1"]
    assert schedule["PortfolioGroup"].tolist() == ["PORT-A"]
    assert schedule["Lane"].tolist() == ["Alpha · P1"]
    assert excluded == 1

    unassigned, excluded = prepare_portfolio_schedule(
        project_rows(),
        "Unassigned",
    )
    assert unassigned["ProjectID"].tolist() == ["P3"]
    assert excluded == 0


def test_portfolio_chart_serializes_full_width_grouped_project_lanes():
    schedule, _ = prepare_portfolio_schedule(project_rows())

    specification = portfolio_timeline_chart(
        schedule,
        pd.DataFrame(),
        "2026-02-15",
    ).to_dict()

    assert "facet" not in specification
    assert "width" not in specification
    assert (
        specification["layer"][0]["encoding"]["y"]["field"]
        == "DisplayLane"
    )
    assert any(
        row["DisplayLane"].startswith("PORT-A · ")
        for row in specification["datasets"][
            next(iter(specification["datasets"]))
        ]
        if row.get("MarkType") == "project"
    )
    parameters = specification.get("params", [])
    assert any(
        parameter["name"] == "project_pick"
        for parameter in parameters
    )


def test_prepare_project_schedule_scopes_and_exposes_invalid_rows():
    schedule, excluded = prepare_project_schedule(schedule_rows(), "P1")

    assert schedule["TaskID"].tolist() == ["T1", "T2"]
    assert schedule["IsMilestone"].tolist() == [False, True]
    assert schedule.loc[1, "PlotFinish"] == pd.Timestamp("2026-02-02")
    assert excluded == 1


def test_findings_for_project_reads_direct_and_record_entities():
    findings = [
        {
            "finding_id": "direct",
            "affected_entities": {"projects": ["P1"]},
        },
        {
            "finding_id": "record",
            "affected_entities": {"records": ["task:T2"]},
        },
        {
            "finding_id": "other",
            "affected_entities": {"projects": ["P2"]},
        },
    ]

    selected = findings_for_project(findings, "P1", ["T1", "T2"])

    assert [finding["finding_id"] for finding in selected] == [
        "direct",
        "record",
    ]


def test_findings_for_projects_includes_task_linked_findings():
    findings = [
        {
            "finding_id": "direct",
            "affected_entities": {"projects": ["P2"]},
        },
        {
            "finding_id": "task",
            "affected_entities": {"tasks": ["T1"]},
        },
        {
            "finding_id": "other",
            "affected_entities": {"projects": ["P9"]},
        },
    ]

    selected = findings_for_projects(findings, ["P1", "P2"], schedule_rows())

    assert [finding["finding_id"] for finding in selected] == [
        "direct",
        "task",
    ]


def test_build_finding_occurrences_uses_supporting_evidence_dates():
    schedule, _ = prepare_project_schedule(schedule_rows(), "P1")
    findings = [
        {
            "finding_id": "SCH-1",
            "title": "Long task",
            "rule_id": "SCH-LONG-TASK",
            "domain": "schedule",
            "severity": "medium",
            "affected_entities": {"tasks": ["T1"]},
            "supporting_artifacts": ["curated/schedule.csv"],
        },
        {
            "finding_id": "RES-1",
            "title": "Conflict",
            "rule_id": "RES-CONFLICT",
            "domain": "resource",
            "severity": "high",
            "affected_entities": {"tasks": ["T1", "T2"]},
            "supporting_artifacts": ["curated/resource.csv"],
        },
    ]
    artifacts = {
        "curated/schedule.csv": pd.DataFrame([{
            "RuleID": "SCH-LONG-TASK",
            "ProjectID": "P1",
            "TaskID": "T1",
            "TaskStart": "2026-01-01",
            "TaskFinish": "2026-01-31",
            "Message": "Task duration exceeds threshold",
        }]),
        "curated/resource.csv": pd.DataFrame([{
            "ProjectIDs": "P1,P2",
            "TaskIDs": "T1,T9",
            "ConflictStart": "2026-01-10",
            "ConflictFinish": "2026-01-12",
            "ResourceName": "Alex",
            "TotalAllocation": 150,
        }]),
    }

    occurrences = build_finding_occurrences(schedule, findings, artifacts)

    assert occurrences[["FindingID", "TaskID"]].to_dict("records") == [
        {"FindingID": "SCH-1", "TaskID": "T1"},
        {"FindingID": "RES-1", "TaskID": "T1"},
    ]
    assert occurrences.iloc[1]["Start"] == pd.Timestamp("2026-01-10")
    assert occurrences.iloc[1]["Detail"] == "Alex: 150% allocation"


def test_project_occurrences_map_project_and_task_evidence_to_summary_bars():
    project_schedule, _ = prepare_portfolio_schedule(project_rows())
    findings = [
        {
            "finding_id": "SCH-1",
            "title": "Long task",
            "rule_id": "SCH-LONG-TASK",
            "domain": "schedule",
            "severity": "medium",
            "affected_entities": {"tasks": ["T1"]},
            "supporting_artifacts": ["curated/schedule.csv"],
        },
        {
            "finding_id": "RES-1",
            "title": "Conflict",
            "rule_id": "RES-CONFLICT",
            "domain": "resource",
            "severity": "high",
            "affected_entities": {"projects": ["P1", "P2"]},
            "supporting_artifacts": ["curated/resource.csv"],
        },
    ]
    artifacts = {
        "curated/schedule.csv": pd.DataFrame([{
            "RuleID": "SCH-LONG-TASK",
            "TaskID": "T1",
            "TaskStart": "2026-01-01",
            "TaskFinish": "2026-01-31",
            "Message": "Task duration exceeds threshold",
        }]),
        "curated/resource.csv": pd.DataFrame([{
            "RuleID": "RES-CONFLICT",
            "ProjectIDs": "P1,P2",
            "ConflictStart": "2026-02-10",
            "ConflictFinish": "2026-02-12",
            "ResourceName": "Alex",
            "TotalAllocation": 150,
        }]),
    }

    occurrences = build_project_finding_occurrences(
        project_schedule,
        schedule_rows(),
        findings,
        artifacts,
    )

    assert occurrences[["FindingID", "ProjectID"]].to_dict("records") == [
        {"FindingID": "SCH-1", "ProjectID": "P1"},
        {"FindingID": "RES-1", "ProjectID": "P1"},
        {"FindingID": "RES-1", "ProjectID": "P2"},
    ]
    assert occurrences.iloc[2]["PortfolioGroup"] == "PORT-B"


def test_selected_finding_id_handles_streamlit_selection_shape():
    event = {"selection": {"finding_pick": [{"FindingID": "SCH-1"}]}}

    assert selected_finding_id(event) == "SCH-1"
    assert selected_finding_id({"selection": {}}) is None


def test_selected_project_id_handles_streamlit_selection_shape():
    event = {"selection": {"project_pick": [{"ProjectID": "P2"}]}}

    assert selected_project_id(event) == "P2"
    assert selected_project_id({"selection": {}}) is None
