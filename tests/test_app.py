import json
from pathlib import Path

from streamlit.testing.v1 import AppTest


def _write_json(path, document):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document), encoding="utf-8")


def write_snapshot(tmp_path, client_id, snapshot_id, observation_date):
    storage = tmp_path / "local-data"
    _write_json(
        storage / "metadata" / client_id / "client.json",
        {"format_version": "1.0", "client_id": client_id},
    )
    snapshot_root = (
        storage / "metadata" / client_id / "snapshots" / snapshot_id
    )
    processed = (
        storage / "processed" / client_id / "snapshots" / snapshot_id
    )
    curated = (
        storage / "curated" / client_id / "snapshots" / snapshot_id
    )
    datasets = {
        "projects": f"{client_id}/snapshots/{snapshot_id}/projects.csv",
        "tasks": f"{client_id}/snapshots/{snapshot_id}/tasks.csv",
    }
    _write_json(snapshot_root / "snapshot.json", {
        "format_version": "1.0",
        "client_id": client_id,
        "snapshot_id": snapshot_id,
        "run_id": f"run-{snapshot_id}",
        "observation_date": observation_date,
        "datasets": datasets,
    })
    _write_json(snapshot_root / "fitness.json", {
        "format_version": "1.0",
        "client_id": client_id,
        "snapshot_id": snapshot_id,
        "capabilities": {
            name: {
                "status": "fit",
                "blocking_conditions": [],
                "caveats": [],
                "unavailable_rules": [],
            }
            for name in (
                "data", "schedule", "resource", "dependency",
                "portfolio", "reporting", "exploratory"
            )
        },
    })
    finding = {
        "finding_id": "SCH-1",
        "domain": "schedule",
        "severity": "high",
        "title": "Test condition",
        "description": "A deterministic test finding.",
        "rule_id": "SCH-TEST",
        "evidence": {"count": 1},
        "affected_entities": {"projects": ["P1"]},
        "supporting_artifacts": [],
    }
    _write_json(snapshot_root / "findings.json", {
        "format_version": "1.0",
        "client_id": client_id,
        "snapshot_id": snapshot_id,
        "finding_count": 1,
        "counts_by_domain": {"schedule": 1},
        "counts_by_severity": {"high": 1},
        "findings": [finding],
    })
    project_health_reference = (
        f"curated/{client_id}/snapshots/{snapshot_id}/"
        "overview/project_health.csv"
    )
    project_profile_reference = (
        f"curated/{client_id}/snapshots/{snapshot_id}/"
        "overview/project_diagnostic_profile.csv"
    )
    schedule_products = {
        "project_summary": (
            f"curated/{client_id}/snapshots/{snapshot_id}/schedule/"
            "project_schedule_health.csv"
        ),
        "activity_profile": (
            f"curated/{client_id}/snapshots/{snapshot_id}/schedule/"
            "schedule_activity_profile.csv"
        ),
        "conditions": (
            f"curated/{client_id}/snapshots/{snapshot_id}/schedule/"
            "schedule_conditions.csv"
        ),
    }
    resource_products = {
        "resource_summary": (
            f"curated/{client_id}/snapshots/{snapshot_id}/resource/"
            "resource_summary.csv"
        ),
        "project_summary": (
            f"curated/{client_id}/snapshots/{snapshot_id}/resource/"
            "project_resource_summary.csv"
        ),
        "conflicts": (
            f"curated/{client_id}/snapshots/{snapshot_id}/resource/"
            "resource_conflicts.csv"
        ),
        "unassigned_work": (
            f"curated/{client_id}/snapshots/{snapshot_id}/resource/"
            "unassigned_work.csv"
        ),
        "assignment_timeline": (
            f"curated/{client_id}/snapshots/{snapshot_id}/resource/"
            "assignment_timeline.csv"
        ),
    }
    dependency_products = {
        "edges": (
            f"curated/{client_id}/snapshots/{snapshot_id}/dependency/"
            "dependency_edges.csv"
        ),
        "task_connectivity": (
            f"curated/{client_id}/snapshots/{snapshot_id}/dependency/"
            "task_connectivity.csv"
        ),
        "project_summary": (
            f"curated/{client_id}/snapshots/{snapshot_id}/dependency/"
            "project_dependency_summary.csv"
        ),
    }
    exploratory_products = {
        "observations": (
            f"curated/{client_id}/snapshots/{snapshot_id}/exploratory/"
            "distribution_observations.csv"
        ),
        "distribution_summary": (
            f"curated/{client_id}/snapshots/{snapshot_id}/exploratory/"
            "distribution_summary.csv"
        ),
        "interestingness": (
            f"curated/{client_id}/snapshots/{snapshot_id}/exploratory/"
            "interestingness.csv"
        ),
    }
    _write_json(snapshot_root / "diagnosis.json", {
        "format_version": "1.0",
        "client_id": client_id,
        "snapshot_id": snapshot_id,
        "execution_status": "success",
        "project_health_object": project_health_reference,
        "project_profile_object": project_profile_reference,
        "diagnostics": [
            {
                "capability": "schedule",
                "diagnostic_id": "schedule_health",
                "status": "success",
                "products": schedule_products,
                "metrics": {
                    "tasks_analysed": 2,
                    "milestone_count": 1,
                    "overdue_tasks": 1,
                    "overdue_milestones": 1,
                    "projects_with_conditions": 1,
                    "date_coverage_pct": 100.0,
                    "hierarchy_coverage_pct": 50.0,
                    "float_coverage_pct": 50.0,
                    "criticality_coverage_pct": 50.0,
                    "unavailable_measures": [
                        "critical_path_network_analysis"
                    ],
                },
            },
            {
                "capability": "resource",
                "diagnostic_id": "resource_conflicts",
                "status": "success",
                "products": resource_products,
                "metrics": {
                    "resources_analysed": 1,
                    "cross_project_resources": 1,
                    "conflict_resource_count": 1,
                    "conflict_count": 1,
                    "task_assignment_coverage_pct": 50.0,
                    "assignment_date_coverage_pct": 100.0,
                    "resource_capacity_coverage_pct": 100.0,
                    "conflict_threshold_pct": 100,
                    "conflict_red_threshold_pct": 130,
                    "capacity_assumption": (
                        "Over-allocation uses concurrent assignment "
                        "allocation above the configured 100% threshold."
                    ),
                    "unavailable_measures": ["true_utilisation"],
                },
            },
            {
                "capability": "dependency",
                "diagnostic_id": "dependency_structure",
                "status": "success",
                "products": dependency_products,
                "metrics": {
                    "dependencies_analysed": 1,
                    "tasks_analysed": 2,
                    "linked_tasks": 2,
                    "dependency_coverage_pct": 100.0,
                    "cross_project_dependencies": 1,
                    "hub_tasks": 0,
                    "bridge_dependencies": 1,
                    "articulation_tasks": 0,
                    "cycle_tasks": 0,
                },
            },
            {
                "capability": "exploratory",
                "diagnostic_id": "distribution_interestingness",
                "status": "success",
                "products": exploratory_products,
                "metrics": {
                    "distribution_count": 2,
                    "observation_count": 4,
                    "interesting_value_count": 1,
                    "unusual_projects": 1,
                    "unusual_resources": 0,
                    "iqr_multiplier": 1.5,
                    "minimum_population": 4,
                    "method": (
                        "Values outside the configured IQR fence are "
                        "flagged; percentile rank is context only."
                    ),
                    "unavailable_metrics": [],
                },
            },
        ],
        "summary": {
            "portfolio_scale": {
                "projects": 2,
                "tasks": 2,
                "milestones": 0,
                "resources": 1,
                "assignments": 2,
                "dependencies": 0,
            },
            "findings": {
                "total": 1,
                "projects_affected": 1,
                "by_domain": {"schedule": 1},
                "by_severity": {"high": 1},
            },
            "diagnostics": {
                "total": 7,
                "completed": 7,
                "skipped": 0,
                "failed": 0,
            },
            "fitness": {
                "blocking_conditions": 0,
                "caveats": 0,
                "unavailable_rules": 0,
            },
        },
    })
    processed.mkdir(parents=True, exist_ok=True)
    (processed / "projects.csv").write_text(
        "ProjectID,ProjectName,PortfolioID,ForecastStartDate,"
        "ForecastFinishDate\n"
        "P1,Alpha,PORT-A,2026-01-01,2026-03-31\n"
        "P2,Beta,PORT-B,2026-02-01,2026-04-30\n",
        encoding="utf-8",
    )
    (processed / "tasks.csv").write_text(
        "TaskID,ProjectID,TaskName,ForecastStartDate,"
        "ForecastFinishDate,IsMilestone\n"
        "T1,P1,Design,2026-01-01,2026-01-31,false\n"
        "T2,P2,Build,2026-02-01,2026-04-15,false\n",
        encoding="utf-8",
    )
    health = curated / "overview" / "project_health.csv"
    health.parent.mkdir(parents=True, exist_ok=True)
    health.write_text(
        "ProjectID,ProjectName,PortfolioID,ProgrammeID,LifecycleStatus,"
        "RAGStatus,TaskCount,PortfolioStatus,ScheduleStatus,"
        "ResourceStatus,ReportingStatus,DependencyStatus,DataFitness,"
        "FindingCount,HighFindings,MediumFindings,LowFindings,FindingIDs\n"
        "P1,Alpha,PORT-A,,Active,Amber,1,No finding,Significant,"
        "No finding,No finding,Not assessed,Fit,1,1,0,0,SCH-1\n"
        "P2,Beta,PORT-B,,Active,Green,1,No finding,No finding,"
        "No finding,No finding,Not assessed,Fit,0,0,0,0,\n",
        encoding="utf-8",
    )
    profile = curated / "overview" / "project_diagnostic_profile.csv"
    profile.write_text(
        "ProjectID,ProjectName,Domain,MetricID,MetricLabel,Value,Unit,"
        "PercentileRank,PopulationCount,Q1,Median,Q3,LowerFence,UpperFence,"
        "OutsideIqr,Availability,AvailabilityReason,SourceDiagnosticID,"
        "SourceProduct\n"
        "P1,Alpha,Portfolio,task_count,Tasks,1,tasks,50,2,1,1,1,1,1,"
        "false,Available,,canonical_observation,processed/tasks.csv\n"
        "P1,Alpha,Schedule,schedule_condition_task_pct,Tasks with schedule "
        "conditions,50,%,100,2,12.5,25,37.5,-25,75,false,Available,,"
        "schedule_health,curated/schedule.csv\n"
        "P1,Alpha,Resources,conflict_resource_pct,Resources with conflicts,"
        "100,%,100,2,25,50,75,-50,150,false,Available,,resource_conflicts,"
        "curated/resource.csv\n"
        "P1,Alpha,Resources,assignment_coverage_pct,Task assignment coverage,"
        "100,%,100,2,25,50,75,-50,150,false,Available,,resource_conflicts,"
        "curated/resource.csv\n"
        "P1,Alpha,Dependencies,average_dependency_connectivity,Average task "
        "connectivity,1,connections,100,2,0.25,0.5,0.75,-0.5,1.5,false,"
        "Available,,dependency_structure,curated/dependency.csv\n"
        "P2,Beta,Portfolio,task_count,Tasks,1,tasks,50,2,1,1,1,1,1,false,"
        "Available,,canonical_observation,processed/tasks.csv\n"
        "P2,Beta,Schedule,schedule_condition_task_pct,Tasks with schedule "
        "conditions,0,%,50,2,12.5,25,37.5,-25,75,false,Available,,"
        "schedule_health,curated/schedule.csv\n"
        "P2,Beta,Resources,conflict_resource_pct,Resources with conflicts,"
        "0,%,50,2,25,50,75,-50,150,false,Available,,resource_conflicts,"
        "curated/resource.csv\n"
        "P2,Beta,Resources,assignment_coverage_pct,Task assignment coverage,"
        "0,%,50,2,25,50,75,-50,150,false,Available,,resource_conflicts,"
        "curated/resource.csv\n"
        "P2,Beta,Dependencies,average_dependency_connectivity,Average task "
        "connectivity,0,connections,50,2,0.25,0.5,0.75,-0.5,1.5,false,"
        "Available,,dependency_structure,curated/dependency.csv\n",
        encoding="utf-8",
    )
    schedule = curated / "schedule"
    schedule.mkdir(parents=True, exist_ok=True)
    (schedule / "project_schedule_health.csv").write_text(
        "ProjectID,ProjectName,TaskCount,OverdueTasks,VeryLongTasks,"
        "TasksStartingBeforeProject,TasksFinishingAfterProject,IssueCount,"
        "ScheduleHealth,MilestoneCount,OverdueMilestones,DateCoveragePct,"
        "HierarchyCoveragePct,FloatCoveragePct,"
        "CriticalEvidenceCoveragePct,BaselineFinishCoveragePct,"
        "MedianTaskDurationDays,MaxTaskDurationDays\n"
        "P1,Alpha,1,1,0,0,0,1,Warning,1,1,100,100,100,100,100,30,30\n"
        "P2,Beta,1,0,0,0,0,0,Healthy,0,0,100,0,0,0,0,73,73\n",
        encoding="utf-8",
    )
    (schedule / "schedule_activity_profile.csv").write_text(
        "ProjectID,ProjectName,TaskID,TaskName,ForecastStart,"
        "ForecastFinish,DurationDays,Status,IsMilestone,IsOverdue,"
        "FinishVarianceDays,TotalFloatDays\n"
        "P1,Alpha,T1,Design,2026-01-01,2026-01-31,30,Active,true,"
        "true,5,2\n"
        "P2,Beta,T2,Build,2026-02-01,2026-04-15,73,Active,false,"
        "false,,\n",
        encoding="utf-8",
    )
    (schedule / "schedule_conditions.csv").write_text(
        "Severity,RuleID,ProjectID,ProjectName,TaskID,TaskName,"
        "TaskStart,TaskFinish,Status,Message\n"
        "medium,SCH-OVERDUE,P1,Alpha,T1,Design,2026-01-01,"
        "2026-01-31,Active,Task is overdue\n",
        encoding="utf-8",
    )
    resource = curated / "resource"
    resource.mkdir(parents=True, exist_ok=True)
    (resource / "resource_summary.csv").write_text(
        "ResourceID,ResourceName,Role,Team,CapacityPct,AssignmentCount,"
        "TaskCount,ProjectCount,ProjectIDs,CrossProject,"
        "AssignmentAllocationSharePct,PeakConcurrentAllocationPct,"
        "ConflictPeriodCount,AssignmentDateCoveragePct\n"
        "R1,Planner,Planner,Controls,100,2,2,2,\"P1,P2\",true,"
        "100,130,1,100\n",
        encoding="utf-8",
    )
    (resource / "project_resource_summary.csv").write_text(
        "ProjectID,TaskCount,AssignedTaskCount,UnassignedTaskCount,"
        "AssignmentCoveragePct,ResourceCount,SharedResourceCount,"
        "ConflictResourceCount,ConflictPeriodCount\n"
        "P1,1,1,0,100,1,1,1,1\n"
        "P2,1,0,1,0,0,0,0,0\n",
        encoding="utf-8",
    )
    (resource / "resource_conflicts.csv").write_text(
        "ResourceName,ResourceID,ConflictStart,ConflictFinish,"
        "TotalAllocation,OverAllocation,ProjectCount,TaskCount,"
        "ProjectIDs,TaskIDs\n"
        "Planner,R1,2026-01-01,2026-01-31,130,30,2,2,"
        "\"P1,P2\",\"T1,T2\"\n",
        encoding="utf-8",
    )
    (resource / "unassigned_work.csv").write_text(
        "ProjectID,TaskID,TaskName,ForecastStart,ForecastFinish,Status\n"
        "P2,T2,Build,2026-02-01,2026-04-15,Active\n",
        encoding="utf-8",
    )
    (resource / "assignment_timeline.csv").write_text(
        "AssignmentID,ResourceID,ResourceName,Role,Team,ProjectID,"
        "TaskID,TaskName,AllocationPct,AssignmentStart,AssignmentFinish,"
        "TaskForecastStart,TaskForecastFinish,DisplayStart,DisplayFinish,"
        "StartDateSource,FinishDateSource,DateSource,DateComplete,"
        "OverlapsConflict,ConflictPeriodCount,PeakConflictAllocationPct,"
        "ConflictStatus\n"
        "A1,R1,Planner,Planner,Controls,P1,T1,Design,70,2026-01-01,"
        "2026-01-31,2026-01-01,2026-01-31,2026-01-01,2026-01-31,"
        "Assignment,Assignment,Assignment dates,true,true,1,130,Red\n"
        "A2,R1,Planner,Planner,Controls,P2,T2,Build,60,,,2026-02-01,"
        "2026-04-15,2026-02-01,2026-04-15,Task forecast,Task forecast,"
        "Task forecast dates,true,false,0,,Green\n",
        encoding="utf-8",
    )
    dependency = curated / "dependency"
    dependency.mkdir(parents=True, exist_ok=True)
    (dependency / "dependency_edges.csv").write_text(
        "DependencyID,PredecessorTaskID,PredecessorTaskName,"
        "PredecessorProjectID,SuccessorTaskID,SuccessorTaskName,"
        "SuccessorProjectID,RelationshipType,LagDays,CrossProject,"
        "IsBridge,InCycle,PredecessorX,PredecessorY,SuccessorX,"
        "SuccessorY\n"
        "D1,T1,Design,P1,T2,Build,P2,FS,0,true,true,false,1,0,-1,0\n",
        encoding="utf-8",
    )
    (dependency / "task_connectivity.csv").write_text(
        "TaskID,TaskName,ProjectID,PredecessorCount,SuccessorCount,"
        "ConnectivityDegree,CrossProjectDependencyCount,IsHub,"
        "IsArticulation,InCycle,NetworkX,NetworkY\n"
        "T1,Design,P1,0,1,1,1,false,false,false,1,0\n"
        "T2,Build,P2,1,0,1,1,false,false,false,-1,0\n",
        encoding="utf-8",
    )
    (dependency / "project_dependency_summary.csv").write_text(
        "ProjectID,TaskCount,DependencyCount,InternalDependencyCount,"
        "CrossProjectIncoming,CrossProjectOutgoing,LinkedTaskCount,"
        "UnlinkedTaskCount,DependencyCoveragePct,HubTaskCount,"
        "ArticulationTaskCount,CycleTaskCount,AverageConnectivity,"
        "MaxConnectivity\n"
        "P1,1,1,0,0,1,1,0,100,0,0,0,1,1\n"
        "P2,1,1,0,1,0,1,0,100,0,0,0,1,1\n",
        encoding="utf-8",
    )
    exploratory = curated / "exploratory"
    exploratory.mkdir(parents=True, exist_ok=True)
    (exploratory / "distribution_observations.csv").write_text(
        "EntityType,EntityID,EntityName,Metric,Value,PercentileRank\n"
        "Project,P1,Alpha,TaskCount,1,50\n"
        "Project,P2,Beta,TaskCount,1,50\n"
        "Project,P1,Alpha,ProjectDurationDays,89,50\n"
        "Project,P2,Beta,ProjectDurationDays,88,100\n",
        encoding="utf-8",
    )
    (exploratory / "distribution_summary.csv").write_text(
        "EntityType,Metric,PopulationCount,EvidenceCount,CoveragePct,"
        "Minimum,Q1,Median,Q3,Maximum,Mean,IQR,LowerFence,UpperFence,"
        "OutlierCount\n"
        "Project,TaskCount,2,2,100,1,1,1,1,1,1,0,1,1,0\n"
        "Project,ProjectDurationDays,2,2,100,88,88.25,88.5,88.75,"
        "89,88.5,0.5,87.5,89.5,0\n",
        encoding="utf-8",
    )
    (exploratory / "interestingness.csv").write_text(
        "EntityType,EntityID,EntityName,Metric,Value,PopulationMedian,"
        "Q1,Q3,LowerFence,UpperFence,PercentileRank,Direction,"
        "RatioToMedian,RuleID,Explanation\n"
        "Project,P1,Alpha,TaskCount,10,1,1,1,1,1,100,High,10,"
        "EXP-PROJECT-TASK-COUNT,TaskCount is outside the high IQR fence.\n",
        encoding="utf-8",
    )


def app_for(tmp_path, monkeypatch):
    monkeypatch.setenv("DATALAB_PLATFORM_PATH", str(tmp_path))
    monkeypatch.delenv("DATA_PLATFORM_STORAGE_ROOT", raising=False)
    app_path = Path(__file__).parents[1] / "app.py"
    return AppTest.from_file(str(app_path), default_timeout=10).run()


def test_workspace_renders_governed_snapshot(tmp_path, monkeypatch):
    snapshot_id = "snapshot-test"
    write_snapshot(tmp_path, "client-001", snapshot_id, "2026-09-01")

    app = app_for(tmp_path, monkeypatch)

    assert not app.exception
    assert app.session_state["selected_snapshot_id"] == snapshot_id
    assert any(
        button.label == "Exit Data Lab" for button in app.button
    )
    assert any(
        metric.label == "Findings" and metric.value == "1"
        for metric in app.metric
    )
    assert any(
        item.value == "Portfolio attention map" for item in app.subheader
    )
    for page in (
        "app_pages/evidence.py",
        "app_pages/findings.py",
        "app_pages/project_health.py",
        "app_pages/schedule.py",
        "app_pages/resources.py",
        "app_pages/dependencies.py",
        "app_pages/patterns.py",
        "app_pages/plan.py",
        "app_pages/history.py",
        "app_pages/interpretations.py",
        "app_pages/run_lab.py",
    ):
        app.switch_page(page).run()
        assert not app.exception, page


def test_project_health_uses_governed_matrix(tmp_path, monkeypatch):
    snapshot_id = "snapshot-health"
    write_snapshot(tmp_path, "client-001", snapshot_id, "2026-09-01")
    app = app_for(tmp_path, monkeypatch)

    app.switch_page("app_pages/project_health.py").run()

    assert not app.exception
    assert any(
        metric.label == "Projects shown" and metric.value == "2"
        for metric in app.metric
    )
    assert len(app.dataframe[0].value) == 2
    assert app.selectbox(key=f"health_project_{snapshot_id}").value == "P1"
    assert any(
        item.value == "Project findings" for item in app.subheader
    )
    assert any(
        item.value == "Project diagnostic fingerprint"
        for item in app.subheader
    )


def test_plan_filters_portfolio_and_drills_into_project(
    tmp_path, monkeypatch,
):
    snapshot_id = "snapshot-plan"
    write_snapshot(tmp_path, "client-001", snapshot_id, "2026-09-01")
    app = app_for(tmp_path, monkeypatch)
    app.switch_page("app_pages/plan.py").run()

    portfolio = app.selectbox(key=f"plan_portfolio_{snapshot_id}")
    portfolio.set_value("PORT-A").run()
    assert not app.exception
    assert any(
        metric.label == "Projects plotted" and metric.value == "1"
        for metric in app.metric
    )
    app.selectbox(
        key=f"plan_project_{snapshot_id}_PORT-A"
    ).set_value("P1").run()
    assert not app.exception
    assert any(
        metric.label == "Tasks plotted" and metric.value == "1"
        for metric in app.metric
    )


def test_schedule_lens_reads_backend_products(tmp_path, monkeypatch):
    snapshot_id = "snapshot-schedule"
    write_snapshot(tmp_path, "client-001", snapshot_id, "2026-09-01")
    app = app_for(tmp_path, monkeypatch)

    app.switch_page("app_pages/schedule.py").run()

    assert not app.exception
    assert any(
        metric.label == "Overdue activities" and metric.value == "1"
        for metric in app.metric
    )
    assert any(
        item.value == "Activity duration distribution"
        for item in app.subheader
    )
    assert any(
        item.value == "Deterministic schedule conditions"
        for item in app.subheader
    )
    app.selectbox(
        key=f"schedule_project_{snapshot_id}"
    ).set_value("P2").run()
    assert not app.exception


def test_resource_lens_reads_backend_products(tmp_path, monkeypatch):
    snapshot_id = "snapshot-resource"
    write_snapshot(tmp_path, "client-001", snapshot_id, "2026-09-01")
    app = app_for(tmp_path, monkeypatch)

    app.switch_page("app_pages/resources.py").run()

    assert not app.exception
    assert any(
        metric.label == "Conflict resources" and metric.value == "1"
        for metric in app.metric
    )
    assert any(
        item.value == "Resource concentration and cross-project usage"
        for item in app.subheader
    )
    app.segmented_control(
        key=f"resource_view_{snapshot_id}"
    ).set_value("By person").run()
    assert not app.exception
    assert any(
        item.value == "Plan on a page by person"
        for item in app.subheader
    )
    assert any(
        metric.label == "Date fallbacks" and metric.value == "1"
        for metric in app.metric
    )
    assert any(
        "Green means no calculated conflict" in item.value
        for item in app.caption
    )
    app.segmented_control(
        key=f"resource_view_{snapshot_id}"
    ).set_value("By project").run()
    assert not app.exception
    assert any(
        item.value == "Compare projects" for item in app.subheader
    )
    app.selectbox(
        key=f"resource_project_{snapshot_id}"
    ).set_value("P2").run()
    assert not app.exception


def test_dependency_lens_reads_backend_graph_products(
    tmp_path, monkeypatch,
):
    snapshot_id = "snapshot-dependency"
    write_snapshot(tmp_path, "client-001", snapshot_id, "2026-09-01")
    app = app_for(tmp_path, monkeypatch)

    app.switch_page("app_pages/dependencies.py").run()

    assert not app.exception
    assert any(
        metric.label == "Cross-project links" and metric.value == "1"
        for metric in app.metric
    )
    assert any(
        item.value == "Dependency network" for item in app.subheader
    )
    assert any(
        "Shows how tasks depend on one another" in item.value
        for item in app.caption
    )
    app.selectbox(
        key=f"dependency_project_{snapshot_id}"
    ).set_value("P1").run()
    assert not app.exception


def test_patterns_lens_reads_saved_distributions(
    tmp_path, monkeypatch,
):
    snapshot_id = "snapshot-patterns"
    write_snapshot(tmp_path, "client-001", snapshot_id, "2026-09-01")
    app = app_for(tmp_path, monkeypatch)

    app.switch_page("app_pages/patterns.py").run()

    assert not app.exception
    assert any(
        metric.label == "Unusual values" and metric.value == "1"
        for metric in app.metric
    )
    assert any(
        item.value == "What is unusual?" for item in app.subheader
    )
    assert any(
        "Summarises the selected measure" in item.value
        for item in app.caption
    )
    assert any(
        "**Number of tasks**" in item.value
        for item in app.markdown
    )
    app.selectbox(
        key=f"patterns_metric_{snapshot_id}"
    ).set_value("TaskCount").run()
    assert not app.exception
    assert any(
        "The number of canonical tasks" in item.value
        for item in app.caption
    )


def test_client_selection_scopes_observations(tmp_path, monkeypatch):
    write_snapshot(tmp_path, "alpha", "snapshot-alpha", "2026-09-01")
    write_snapshot(
        tmp_path, "alpha", "snapshot-alpha-old", "2026-08-01"
    )
    write_snapshot(tmp_path, "beta", "snapshot-beta", "2026-09-01")
    app = app_for(tmp_path, monkeypatch)

    assert app.session_state["selected_client_id"] == "alpha"
    app.selectbox(key="client_selector").select("beta").run()
    assert not app.exception
    assert app.session_state["selected_client_id"] == "beta"
    assert app.session_state["selected_snapshot_id"] == "snapshot-beta"


def test_exit_button_requests_server_shutdown(tmp_path, monkeypatch):
    write_snapshot(
        tmp_path, "client-001", "snapshot-test", "2026-09-01"
    )
    from components import exit_control

    shutdown_requests = []
    monkeypatch.setattr(
        exit_control,
        "request_streamlit_shutdown",
        lambda: shutdown_requests.append(True),
    )
    app = app_for(tmp_path, monkeypatch)
    app.button(key="exit_application").click().run()

    assert shutdown_requests == [True]
    assert not app.exception


def test_raw_only_client_can_open_inspection(tmp_path, monkeypatch):
    inbox = tmp_path / "local-data" / "raw" / "new-client"
    inbox.mkdir(parents=True)
    (inbox / "projects.csv").write_text(
        "ProjectID\nP1\n", encoding="utf-8"
    )
    app = app_for(tmp_path, monkeypatch)
    app.switch_page("app_pages/run_lab.py").run()

    assert not app.exception
    assert app.session_state["selected_client_id"] == "new-client"
    inspect_button = next(
        button for button in app.button
        if button.label == "Inspect raw evidence"
    )
    assert not inspect_button.disabled
