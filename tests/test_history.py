import pandas as pd

from components.history_charts import delivery_trajectory_chart
from services.history import (
    delivery_project_facts,
    delivery_trajectory_metrics,
    history_fitness_counts,
    history_product_label,
    history_scope_frame,
    prepare_delivery_trajectory,
    scope_delivery_trajectory,
    selected_trajectory_project_id,
)


def test_history_product_label_and_scope_keep_identity_types_distinct():
    product = {
        "trend_id": "trend-001",
        "from_observation_date": "2026-01-31",
        "to_observation_date": "2026-03-31",
        "observation_dates": ["2026-01-31", "2026-02-28", "2026-03-31"],
        "snapshot_ids": ["snapshot-a", "snapshot-b", "snapshot-c"],
    }

    assert history_product_label(product, "trend_id") == (
        "2026-01-31 to 2026-03-31 · trend-001"
    )
    assert history_scope_frame(product).to_dict("records") == [
        {
            "Sequence": 1,
            "Observation date": "2026-01-31",
            "Snapshot ID": "snapshot-a",
        },
        {
            "Sequence": 2,
            "Observation date": "2026-02-28",
            "Snapshot ID": "snapshot-b",
        },
        {
            "Sequence": 3,
            "Observation date": "2026-03-31",
            "Snapshot ID": "snapshot-c",
        },
    ]


def test_history_fitness_counts_saved_limitations_without_reclassification():
    product = {
        "fitness": [
            {
                "assessment": {
                    "status": "fit_with_caveats",
                    "caveats": [{"rule_id": "FIT-1"}],
                    "blocking_conditions": [],
                    "unavailable_rules": ["HIS-1"],
                }
            },
            {
                "assessment": {
                    "status": "not_fit",
                    "caveats": [{"rule_id": "FIT-2"}, {"rule_id": "FIT-3"}],
                    "blocking_conditions": [{"rule_id": "FIT-4"}],
                    "unavailable_rules": [],
                }
            },
        ]
    }

    assert history_fitness_counts(product) == {
        "assessments": 2,
        "with_caveats": 2,
        "caveats": 3,
        "blocking_conditions": 1,
        "unavailable_rules": 1,
    }


def observation_rows():
    return pd.DataFrame([
        {
            "ObservationIndex": 1,
            "SnapshotID": "S1",
            "ObservationDate": "2026-01-31",
            "ProjectID": "P1",
            "ProjectName": "Alpha",
            "FinishDate": "2026-06-30",
            "Status": "amber",
        },
        {
            "ObservationIndex": 2,
            "SnapshotID": "S2",
            "ObservationDate": "2026-02-28",
            "ProjectID": "P1",
            "ProjectName": "Alpha",
            "FinishDate": "2026-07-10",
            "Status": "red",
        },
        {
            "ObservationIndex": 3,
            "SnapshotID": "S3",
            "ObservationDate": "2026-03-31",
            "ProjectID": "P1",
            "ProjectName": "Alpha",
            "FinishDate": "2026-07-15",
            "Status": "red",
        },
        {
            "ObservationIndex": 1,
            "SnapshotID": "S1",
            "ObservationDate": "2026-01-31",
            "ProjectID": "P2",
            "ProjectName": "Beta",
            "FinishDate": "2026-08-31",
            "Status": "green",
        },
        {
            "ObservationIndex": 3,
            "SnapshotID": "S3",
            "ObservationDate": "2026-03-31",
            "ProjectID": "P2",
            "ProjectName": "Beta",
            "FinishDate": "2026-09-30",
            "Status": "amber",
        },
        {
            "ObservationIndex": 1,
            "SnapshotID": "S1",
            "ObservationDate": "2026-01-31",
            "ProjectID": "P3",
            "ProjectName": "Gamma",
            "FinishDate": "2026-05-31",
            "Status": "green",
        },
        {
            "ObservationIndex": 2,
            "SnapshotID": "S2",
            "ObservationDate": "2026-02-28",
            "ProjectID": "P3",
            "ProjectName": "Gamma",
            "FinishDate": "2026-05-31",
            "Status": "green",
        },
    ])


def summary_rows():
    return pd.DataFrame([
        {
            "ProjectID": "P1",
            "FinishDateMovementCount": 2,
            "FinishDateSlippageCount": 2,
            "TotalDaysSlipped": 15,
            "StatusMovementCount": 1,
            "UnavailableAdjacentTransitions": 0,
        },
        {
            "ProjectID": "P2",
            "FinishDateMovementCount": 0,
            "FinishDateSlippageCount": 0,
            "TotalDaysSlipped": 0,
            "StatusMovementCount": 0,
            "UnavailableAdjacentTransitions": 2,
        },
        {
            "ProjectID": "P3",
            "FinishDateMovementCount": 0,
            "FinishDateSlippageCount": 0,
            "TotalDaysSlipped": 0,
            "StatusMovementCount": 0,
            "UnavailableAdjacentTransitions": 0,
        },
    ])


def test_prepare_delivery_trajectory_uses_summary_and_breaks_gaps():
    trajectory, excluded = prepare_delivery_trajectory(
        observation_rows(),
        summary_rows(),
    )

    alpha = trajectory.loc[trajectory["ProjectID"].eq("P1")]
    beta = trajectory.loc[trajectory["ProjectID"].eq("P2")]

    assert alpha["CumulativeMovementDays"].tolist() == [0, 10, 15]
    assert alpha["Status"].tolist() == ["Amber", "Red", "Red"]
    assert alpha.iloc[-1]["EndLabel"] == "P1 +15d"
    assert beta["CumulativeMovementDays"].tolist() == [0, 0]
    assert beta["TrajectorySeries"].nunique() == 2
    assert excluded == 0


def test_delivery_metrics_and_mover_scope_use_trend_summary():
    trajectory, _ = prepare_delivery_trajectory(
        observation_rows(),
        summary_rows(),
    )

    assert delivery_trajectory_metrics(summary_rows()) == {
        "projects_moved": 1,
        "projects_slipped": 1,
        "total_days_slipped": 15,
        "status_changes": 1,
    }
    assert scope_delivery_trajectory(
        trajectory,
        movers_only=True,
    )["ProjectID"].unique().tolist() == ["P1"]


def test_delivery_project_facts_remain_factual():
    trajectory, _ = prepare_delivery_trajectory(
        observation_rows(),
        summary_rows(),
    )

    facts = delivery_project_facts(trajectory, "P1")

    assert facts["net_movement_days"] == 15
    assert facts["slippage_transitions"] == 2
    assert facts["status_path"] == "Amber → Red"
    assert facts["latest_finish"] == pd.Timestamp("2026-07-15")


def test_delivery_project_facts_do_not_describe_change_across_a_gap():
    trajectory, _ = prepare_delivery_trajectory(
        observation_rows(),
        summary_rows(),
    )

    facts = delivery_project_facts(trajectory, "P2")

    assert facts["net_movement_days"] == 0
    assert facts["status_path"] == "Amber → Amber"
    assert facts["unavailable_transitions"] == 2


def test_delivery_chart_exposes_selection_and_rag_context():
    trajectory, _ = prepare_delivery_trajectory(
        observation_rows(),
        summary_rows(),
    )
    chart = delivery_trajectory_chart(
        scope_delivery_trajectory(trajectory, movers_only=True)
    )

    specification = chart.to_dict()

    assert any(
        parameter["name"] == "trajectory_pick"
        for parameter in specification.get("params", [])
    )
    assert any(
        layer.get("encoding", {}).get("color", {}).get("field") == "Status"
        for layer in specification["layer"]
    )


def test_selected_trajectory_project_id_handles_selection_shape():
    event = {"selection": {"trajectory_pick": [{"ProjectID": "P2"}]}}

    assert selected_trajectory_project_id(event) == "P2"
    assert selected_trajectory_project_id({"selection": {}}) is None
