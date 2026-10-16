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
        "resources": f"{client_id}/snapshots/{snapshot_id}/resources.csv",
        "assignments": f"{client_id}/snapshots/{snapshot_id}/assignments.csv",
        "dependencies": f"{client_id}/snapshots/{snapshot_id}/dependencies.csv",
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
        "finding_id": "DCMA-01-LOGIC-1",
        "diagnostic_id": "dcma_14_point",
        "domain": "schedule",
        "severity": "high",
        "title": "Missing schedule logic exceeds the DCMA tripwire",
        "description": "DCMA metric 1 was outside its configured tripwire.",
        "rule_id": "DCMA-01-LOGIC",
        "evidence": {"projects_outside_threshold": 1},
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
            "dcma_14_point_project_summary.csv"
        ),
        "assessment": (
            f"curated/{client_id}/snapshots/{snapshot_id}/schedule/"
            "dcma_14_point_assessment.csv"
        ),
        "activity_profile": (
            f"curated/{client_id}/snapshots/{snapshot_id}/schedule/"
            "schedule_activity_profile.csv"
        ),
        "conditions": (
            f"curated/{client_id}/snapshots/{snapshot_id}/schedule/"
            "dcma_14_point_conditions.csv"
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
                "diagnostic_id": "dcma_14_point",
                "status": "success",
                "products": schedule_products,
                "metrics": {
                    "projects_analysed": 2,
                    "tasks_analysed": 2,
                    "milestone_count": 1,
                    "project_metric_results": 28,
                    "metrics_assessed": 22,
                    "metrics_outside_threshold": 1,
                    "metrics_not_assessable": 6,
                    "projects_outside_threshold": 1,
                    "working_day_basis": "monday_friday_no_holidays",
                    "unavailable_measures": [
                        {
                            "rule_id": "DCMA-12-CRITICAL-PATH-TEST",
                            "metric_number": 12,
                            "metric_name": "Critical Path Test",
                            "reasons": [
                                "Calendar-aware network recalculation is unavailable"
                            ],
                        },
                        {
                            "rule_id": "DCMA-13-CPLI",
                            "metric_number": 13,
                            "metric_name": "Critical Path Length Index (CPLI)",
                            "reasons": [
                                "Critical path length cannot be established"
                            ],
                        },
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
    (processed / "resources.csv").write_text(
        "ResourceID,ResourceName,Role,Team,Capacity\n"
        "R1,Planner,Planner,Controls,100\n",
        encoding="utf-8",
    )
    (processed / "assignments.csv").write_text(
        "AssignmentID,TaskID,ResourceID,Allocation,AssignmentStartDate,"
        "AssignmentFinishDate\n"
        "A1,T1,R1,60,2026-01-01,2026-01-31\n"
        "A2,T2,R1,70,2026-02-01,2026-04-15\n",
        encoding="utf-8",
    )
    (processed / "dependencies.csv").write_text(
        "DependencyID,PredecessorTaskID,SuccessorTaskID,DependencyType,Lag\n"
        "D1,T1,T2,FS,0\n",
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
        "No finding,No finding,Not assessed,Fit,1,1,0,0,DCMA-01-LOGIC-1\n"
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
        "dcma_14_point,curated/schedule.csv\n"
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
        "dcma_14_point,curated/schedule.csv\n"
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
    (schedule / "dcma_14_point_project_summary.csv").write_text(
        "ProjectID,ProjectName,TaskCount,EligibleActivityCount,"
        "AssessableMetrics,OutOfThresholdMetrics,NotAssessableMetrics,"
        "AssessmentStatus,DCMA01Value,DCMA01Status,MilestoneCount,"
        "CompletedTasks,TasksWithBaseline,BaselineCoveragePct,TasksWithFloat,"
        "FloatCoveragePct,CriticalTasks,TasksWithCriticalEvidence,"
        "CriticalEvidenceCoveragePct,MedianTaskDurationDays,"
        "MaxTaskDurationDays,MedianBaselineDurationWorkingDays,"
        "MaxBaselineDurationWorkingDays\n"
        "P1,Alpha,1,1,11,1,3,Outside threshold,100,outside_threshold,"
        "1,0,1,100,1,100,1,1,100,30,30,22,22\n"
        "P2,Beta,1,1,11,0,3,Within assessed thresholds,0,"
        "within_threshold,0,0,1,100,0,0,0,1,100,73,73,52,52\n",
        encoding="utf-8",
    )
    (schedule / "dcma_14_point_assessment.csv").write_text(
        "ProjectID,ProjectName,MetricNumber,RuleID,MetricName,Status,"
        "Numerator,Denominator,Value,Unit,Comparison,Threshold,"
        "EvidenceCoveragePct,StatusDate,StatusDateSource,Population,Reason,"
        "WorkingDayBasis\n"
        "P1,Alpha,1,DCMA-01-LOGIC,Logic,outside_threshold,1,1,100,%,"
        "maximum,5,100,2026-09-01,project_data_date,incomplete baselined "
        "activities,,monday_friday_no_holidays\n"
        "P1,Alpha,12,DCMA-12-CRITICAL-PATH-TEST,Critical Path Test,"
        "not_assessable,,,,result,pass,,,2026-09-01,project_data_date,"
        "project critical path,Calendar-aware network recalculation is "
        "unavailable,monday_friday_no_holidays\n"
        "P1,Alpha,13,DCMA-13-CPLI,Critical Path Length Index (CPLI),"
        "not_assessable,,,,index,minimum,0.95,,2026-09-01,"
        "project_data_date,project critical path,Critical path length cannot "
        "be established,monday_friday_no_holidays\n"
        "P2,Beta,1,DCMA-01-LOGIC,Logic,within_threshold,0,1,0,%,maximum,"
        "5,100,2026-09-01,snapshot_observation_date,incomplete baselined "
        "activities,,monday_friday_no_holidays\n"
        "P2,Beta,12,DCMA-12-CRITICAL-PATH-TEST,Critical Path Test,"
        "not_assessable,,,,result,pass,,,2026-09-01,"
        "snapshot_observation_date,project critical path,Calendar-aware "
        "network recalculation is unavailable,monday_friday_no_holidays\n"
        "P2,Beta,13,DCMA-13-CPLI,Critical Path Length Index (CPLI),"
        "not_assessable,,,,index,minimum,0.95,,2026-09-01,"
        "snapshot_observation_date,project critical path,Critical path length "
        "cannot be established,monday_friday_no_holidays\n",
        encoding="utf-8",
    )
    (schedule / "schedule_activity_profile.csv").write_text(
        "ProjectID,ProjectName,TaskID,TaskName,BaselineStart,BaselineFinish,"
        "BaselineDurationWorkingDays,ForecastStart,ForecastFinish,"
        "ForecastDurationDays,ActualStart,ActualFinish,Status,PercentComplete,"
        "IsMilestone,MilestoneEvidenceAvailable,IsComplete,IsCritical,"
        "CriticalEvidenceAvailable,TotalFloatDays,FloatEvidenceAvailable,"
        "ConstraintType,MissingLogic,HasHardConstraint,HasHighFloat,"
        "HasNegativeFloat,HasHighDuration,HasInvalidDate,MissingResource,"
        "IsMissedTask,BaselineDueNotComplete\n"
        "P1,Alpha,T1,Design,2026-01-01,2026-01-31,22,2026-01-01,"
        "2026-01-31,30,,,Active,50,true,true,false,true,true,-2,true,,true,"
        "false,false,true,false,false,false,false,false\n"
        "P2,Beta,T2,Build,2026-02-01,2026-04-15,52,2026-02-01,"
        "2026-04-15,73,,,Active,25,false,true,false,false,true,,false,,false,"
        "false,false,false,true,false,false,false,false\n",
        encoding="utf-8",
    )
    (schedule / "dcma_14_point_conditions.csv").write_text(
        "RuleID,MetricNumber,MetricName,ProjectID,ProjectName,EntityType,"
        "EntityID,TaskID,TaskName,DependencyID,Condition,ObservedValue,"
        "Threshold,StatusDate,Message\n"
        "DCMA-01-LOGIC,1,Logic,P1,Alpha,task,T1,T1,Design,,missing_logic,"
        "successor,5,2026-09-01,Eligible activity is missing successor logic\n",
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


def write_comparison(tmp_path, client_id):
    comparison_id = "comparison-test"
    metadata = (
        tmp_path / "local-data" / "metadata" / client_id
        / "comparisons" / comparison_id
    )
    curated = (
        tmp_path / "local-data" / "curated" / client_id
        / "comparisons" / comparison_id
    )
    _write_json(metadata / "comparison.json", {
        "client_id": client_id,
        "comparison_id": comparison_id,
        "from_observation_date": "2026-08-01",
        "to_observation_date": "2026-09-01",
        "from_snapshot_id": "snapshot-old",
        "to_snapshot_id": "snapshot-test",
        "change_count": 1,
        "finding_count": 1,
        "execution_status": "completed_with_limitations",
        "comparability_contract": ["client_id", "observation_date"],
        "fitness": {
            "from": {
                "status": "fit_with_caveats",
                "blocking_conditions": [],
                "caveats": [{"rule_id": "FIT-1"}],
                "unavailable_rules": [],
            },
            "to": {
                "status": "fit",
                "blocking_conditions": [],
                "caveats": [],
                "unavailable_rules": [],
            },
        },
        "detailed_output": (
            f"{client_id}/comparisons/{comparison_id}/project_changes.csv"
        ),
        "findings_object": (
            f"{client_id}/comparisons/{comparison_id}/findings.json"
        ),
    })
    _write_json(metadata / "findings.json", {
        "client_id": client_id,
        "comparison_id": comparison_id,
        "finding_count": 1,
        "findings": [{
            "finding_id": "HIS-1",
            "domain": "schedule",
            "severity": "medium",
            "title": "Forecast movement identified",
            "description": "One project moved later.",
            "rule_id": "HIS-FINISH-SLIPPAGE",
            "evidence": {"projects_affected": 1},
            "affected_entities": {"projects": ["P1"]},
        }],
    })
    curated.mkdir(parents=True, exist_ok=True)
    (curated / "project_changes.csv").write_text(
        "ProjectID,FinishDateMovementDays\nP1,5\n",
        encoding="utf-8",
    )


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
    assert len(app.metric) == 4
    assert any(
        metric.label == "Evidence fitness" and metric.value == "7/7 fit"
        for metric in app.metric
    )
    assert any(
        item.value == "Portfolio attention map" for item in app.subheader
    )
    assert any(
        item.value == "From evidence to better decisions"
        for item in app.title
    )
    assert any(
        "Observation" in item.value and "2026-09-01" in item.value
        for item in app.caption
    )
    assert any(
        "Snapshot" in item.value and snapshot_id in item.value
        for item in app.caption
    )
    assert any(
        "Balance portfolio position" in item.value
        for item in app.markdown
    )


def test_history_renders_governed_comparison_and_limitations(
    tmp_path, monkeypatch,
):
    write_snapshot(tmp_path, "client-001", "snapshot-test", "2026-09-01")
    write_comparison(tmp_path, "client-001")
    app = app_for(tmp_path, monkeypatch)

    app.switch_page("app_pages/history.py").run()

    assert not app.exception
    assert any(
        metric.label == "Observed changes" and metric.value == "1"
        for metric in app.metric
    )
    assert any(
        metric.label == "Compared observations" and metric.value == "2"
        for metric in app.metric
    )
    assert any(
        item.value == "Recorded historical findings"
        for item in app.subheader
    )
    assert any(
        item.value == "Governed change evidence"
        for item in app.subheader
    )
    assert any(
        "do not by themselves prove unchanged portfolio scope" in item.value
        for item in app.info
    )
    pages = {
        "app_pages/projects_findings.py": (
            "Where is attention concentrated?",
            "Compare cross-domain project conditions",
        ),
        "app_pages/schedule_plan.py": (
            "Where is the plan exposed?",
            "Review deterministic schedule conditions",
        ),
        "app_pages/resources.py": (
            "Where is capacity under pressure?",
            "Review allocation pressure",
        ),
        "app_pages/structure_patterns.py": (
            "Where is delivery coupled?",
            "Review governed dependency structure",
        ),
        "app_pages/history.py": (
            "What changed—and what keeps happening?",
            "Compare governed observations",
        ),
        "app_pages/scenario_planning.py": (
            "What could improve the plan?",
            "Compare bounded, feasible schedule options",
        ),
        "app_pages/run_lab.py": (
            "Turn evidence into a governed observation",
            "Move from inspection to assessment",
        ),
    }
    for page, (title, description) in pages.items():
        app.switch_page(page).run()
        assert not app.exception, page
        assert any(item.value == title for item in app.title), page
        assert any(
            description in item.value for item in app.markdown
        ), page


def test_sidebar_orders_identity_navigation_and_data_scope(
    tmp_path, monkeypatch,
):
    write_snapshot(tmp_path, "client-001", "snapshot-test", "2026-09-01")

    app = app_for(tmp_path, monkeypatch)

    assert not app.exception
    sidebar = list(app.sidebar.children.values())
    assert [(item.type, item.value) for item in sidebar[:2]] == [
        ("header", "Data Lab"),
        ("markdown", "**Review**"),
    ]
    assert [item.value for item in sidebar[2:8]] == [
        "Workspace",
        "Projects & findings",
        "Schedule & plan",
        "Resources",
        "Structure & patterns",
        "History",
    ]
    assert (sidebar[8].type, sidebar[8].value) == ("markdown", "**Act**")
    assert [item.value for item in sidebar[9:11]] == [
        "Scenario planning",
        "Run the lab",
    ]
    assert (sidebar[11].type, sidebar[11].value) == (
        "subheader",
        "Data scope",
    )


def test_combined_navigation_switches_workspace_and_finding_views(
    tmp_path, monkeypatch,
):
    snapshot_id = "snapshot-combined-views"
    write_snapshot(tmp_path, "client-001", snapshot_id, "2026-09-01")
    app = app_for(tmp_path, monkeypatch)

    app.segmented_control(
        key="workspace_review_view"
    ).set_value("Evidence & fitness").run()
    assert not app.exception
    assert any(
        item.value == "Can this evidence support the analysis?"
        for item in app.title
    )
    assert any(
        item.value == "Fitness by capability" for item in app.subheader
    )

    app.switch_page("app_pages/projects_findings.py").run()
    app.segmented_control(
        key="projects_findings_view"
    ).set_value("All findings").run()
    assert not app.exception
    assert any(
        item.value == "What is happening?" for item in app.title
    )
    assert any(
        metric.label == "Total findings" and metric.value == "1"
        for metric in app.metric
    )
    assert any(
        item.value == "Findings and evidence" for item in app.subheader
    )
    assert any(
        item.value == "Missing schedule logic exceeds the DCMA tripwire"
        for item in app.subheader
    )
    assert any(
        item.value == "**Deterministic condition**"
        for item in app.markdown
    )
    app.segmented_control(
        key="finding_detail_DCMA-01-LOGIC-1"
    ).set_value("Evidence").run()
    assert not app.exception
    assert any(
        item.value == "No supporting artifact references were recorded."
        for item in app.caption
    )


def test_project_health_uses_governed_matrix(tmp_path, monkeypatch):
    snapshot_id = "snapshot-health"
    write_snapshot(tmp_path, "client-001", snapshot_id, "2026-09-01")
    app = app_for(tmp_path, monkeypatch)

    app.switch_page("app_pages/projects_findings.py").run()

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
    app.switch_page("app_pages/schedule_plan.py").run()
    app.segmented_control(
        key="schedule_plan_view"
    ).set_value("Plan on a page").run()

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


def test_scenario_planning_uses_observed_horizon_defaults(
    tmp_path, monkeypatch,
):
    from services import scenario_planning

    monkeypatch.setattr(
        scenario_planning,
        "schedule_platform_ready",
        lambda settings: (True, "test SchedulePlatform"),
    )
    snapshot_id = "snapshot-scenarios"
    write_snapshot(tmp_path, "client-001", snapshot_id, "2026-09-01")
    app = app_for(tmp_path, monkeypatch)

    app.switch_page("app_pages/scenario_planning.py").run()

    assert not app.exception
    assert app.date_input(
        key=f"scenario_horizon_start_{snapshot_id}"
    ).value.isoformat() == "2026-01-01"
    assert app.date_input(
        key=f"scenario_horizon_end_{snapshot_id}"
    ).value.isoformat() == "2026-04-30"
    assert any(
        "The observed baseline spans 01 Jan 2026 to 30 Apr 2026"
        in item.value
        for item in app.caption
    )
    assert any(
        "Execution backend: bounded deterministic search" in item.value
        for item in app.caption
    )
    assert not any(
        "CP-SAT" in item.label
        for item in [*app.selectbox, *app.segmented_control]
    )


def test_scenario_planning_presents_v1_1_contract_and_horizon_failure(
    tmp_path, monkeypatch,
):
    from services import scenario_planning

    snapshot_id = "snapshot-provenance"
    write_snapshot(tmp_path, "client-001", snapshot_id, "2026-09-01")
    monkeypatch.setattr(
        scenario_planning,
        "schedule_platform_ready",
        lambda settings: (True, "schedule-platform 1.1-test"),
    )
    package = {
        "root": tmp_path / "scenario-output" / "run-contract",
        "run": {
            "run_id": "run-contract",
            "client_id": "client-001",
            "snapshot_id": snapshot_id,
            "generation_id": "generation-contract",
            "completed_at": "2026-10-16T09:00:00+00:00",
            "configuration_fingerprint": "sha256:contract-fingerprint",
            "engine_version": "engine-1.1.0",
            "rule_set_version": "rules-2026.10",
        },
        "configuration": {
            "config_version": "1.1",
            "planning": {
                "objective": "protect_priority",
                "planning_horizon": {
                    "start_date": "2026-01-01",
                    "end_date": "2026-12-31",
                },
                "candidate_limit": 250,
                "max_action_depth": 5,
                "allowed_actions": ["move_task_dates"],
            },
        },
        "generation": {
            "status": "no_feasible_scenario",
            "selected_candidates": [],
            "candidates_evaluated": 1,
            "states_deduplicated": 0,
            "search_truncated": False,
            "warnings": [],
            "baseline": {
                "status": "fit",
                "input_fitness": {"conditions": []},
                "observed_conditions": [],
                "engine_version": "engine-1.1.0",
                "rule_set_version": "rules-2026.10",
            },
            "evaluated_candidates": [{
                "proposal": {"proposal_id": "proposal-late"},
                "result": {
                    "feasibility_status": "infeasible",
                    "constraint_violations": [{
                        "code": "PLANNING-HORIZON-EXCEEDED",
                        "message": "The moved task finishes after 2026-12-31.",
                    }],
                },
            }],
        },
    }
    monkeypatch.setattr(
        scenario_planning,
        "list_generation_packages",
        lambda settings, client_id, selected_snapshot_id: [package],
    )
    app = app_for(tmp_path, monkeypatch)

    app.switch_page("app_pages/scenario_planning.py").run()

    assert not app.exception
    metrics = {metric.label: metric.value for metric in app.metric}
    assert metrics["Config version"] == "1.1"
    assert metrics["Planning horizon"] == "2026-01-01 → 2026-12-31"
    assert metrics["Generation method"] == "Bounded deterministic search"
    assert metrics["Candidate limit"] == "250"
    assert metrics["Action depth"] == "5"
    assert metrics["Engine"] == "engine-1.1.0"
    assert metrics["Rules"] == "rules-2026.10"
    assert any(
        "sha256:contract-fingerprint" in item.value for item in app.caption
    )
    assert any(
        "exceeded the configured planning horizon" in item.value
        for item in app.error
    )


def test_schedule_assessment_reads_backend_products(tmp_path, monkeypatch):
    snapshot_id = "snapshot-schedule"
    write_snapshot(tmp_path, "client-001", snapshot_id, "2026-09-01")
    app = app_for(tmp_path, monkeypatch)

    app.switch_page("app_pages/schedule_plan.py").run()

    assert not app.exception
    assert any(
        metric.label == "Outside tripwire" and metric.value == "1"
        for metric in app.metric
    )
    assert any(
        item.value == "Portfolio assessment overview"
        for item in app.subheader
    )
    assert any(
        item.value == "Project assessment coverage"
        for item in app.subheader
    )
    app.selectbox(
        key=f"schedule_overview_project_{snapshot_id}"
    ).set_value("P2").run()
    assert not app.exception
    assert len(app.dataframe[0].value) == 1

    app.segmented_control(
        key=f"schedule_assessment_view_{snapshot_id}"
    ).set_value("Metric detail").run()
    assert not app.exception
    assert any(
        item.value == "Metric results and supporting evidence"
        for item in app.subheader
    )
    app.selectbox(
        key=f"schedule_detail_metric_{snapshot_id}"
    ).set_value(1).run()
    assert not app.exception
    assert len(app.dataframe[0].value) == 2
    assert len(app.dataframe[1].value) == 1

    app.segmented_control(
        key=f"schedule_assessment_view_{snapshot_id}"
    ).set_value("Activity evidence").run()
    assert not app.exception
    assert any(
        item.value == "Activity evidence" for item in app.subheader
    )
    assert any(
        item.value == "Milestone position" for item in app.subheader
    )


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

    app.switch_page("app_pages/structure_patterns.py").run()

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

    app.switch_page("app_pages/structure_patterns.py").run()
    app.segmented_control(
        key="structure_patterns_view"
    ).set_value("Patterns").run()

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
    assert any(
        metric.label == "Selected client" and metric.value == "new-client"
        for metric in app.metric
    )
    assert any(
        "Run ID records technical processing" in item.value
        for item in app.caption
    )


def test_run_lab_opens_first_actionable_stage_and_allows_review(
    tmp_path, monkeypatch,
):
    write_snapshot(
        tmp_path, "client-001", "snapshot-test", "2026-09-01"
    )
    app = app_for(tmp_path, monkeypatch)

    app.switch_page("app_pages/run_lab.py").run()

    assert not app.exception
    assert app.segmented_control(key="run_lab_stage").value == "3 · Diagnose"
    assert any(button.label == "Run diagnosis" for button in app.button)
    assert not any(
        button.label == "Inspect raw evidence" for button in app.button
    )

    app.segmented_control(key="run_lab_stage").set_value(
        "1 · Inspect"
    ).run()

    assert not app.exception
    assert any(
        button.label == "Inspect raw evidence" for button in app.button
    )
