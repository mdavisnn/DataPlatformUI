"""Tests for consultant-friendly capability fitness details."""

import pandas as pd

from services.fitness import (
    capability_condition_frame,
    unavailable_rule_frame,
)


def test_old_fitness_summary_is_expanded_to_field_level_evidence():
    assessment = {
        "caveats": [{
            "rule_id": "FIT-OPTIONAL-FIELD",
            "dataset": "projects",
            "count": 2,
        }],
    }
    evidence = pd.DataFrame([
        {
            "rule_id": "FIT-OPTIONAL-FIELD",
            "dataset": "projects",
            "field": "ProjectManager",
        },
        {
            "rule_id": "FIT-OPTIONAL-FIELD",
            "dataset": "projects",
            "field": "RAGStatus",
        },
    ])

    frame = capability_condition_frame(
        assessment, "caveats", evidence
    )

    assert set(frame["Field"]) == {"ProjectManager", "RAGStatus"}
    assert set(frame["Rule"]) == {"Optional field is incomplete"}
    assert frame["What this means"].str.contains(
        "useful but not essential"
    ).all()


def test_unavailable_rule_has_lay_explanation():
    assessment = {
        "unavailable_rules": [{
            "rule_id": "SCH-NO-ASSIGNMENT",
            "rule_title": "Tasks without assignments",
            "unfit_datasets": ["assignments"],
        }],
    }

    frame = unavailable_rule_frame(assessment)

    assert frame.loc[0, "Analysis"] == "Tasks without assignments"
    assert frame.loc[0, "Unavailable evidence"] == "assignments"
    assert "was not run" in frame.loc[0, "What this means"]
