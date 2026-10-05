import pandas as pd

from services.findings import (
    affected_entities_frame,
    capability_for_finding,
    filter_evidence_for_finding,
    filter_findings,
    finding_evidence_frame,
    sort_findings,
)


FINDINGS = [
    {
        "finding_id": "LOW-1",
        "domain": "schedule",
        "severity": "low",
        "title": "Later title",
        "rule_id": "RULE-LOW",
    },
    {
        "finding_id": "HIGH-1",
        "domain": "resource",
        "severity": "high",
        "title": "Earlier title",
        "rule_id": "RULE-HIGH",
        "evidence": {
            "threshold_percentage": 100,
            "excluded_reasons": ["missing dates", "missing allocation"],
        },
        "affected_entities": {
            "projects": ["P1", "P2"],
            "resources": ["R1"],
        },
    },
]


def test_findings_can_be_filtered_and_sorted_without_reclassification():
    selected = filter_findings(
        FINDINGS,
        domains=["Resource"],
        severities=["High"],
    )

    assert [item["finding_id"] for item in selected] == ["HIGH-1"]
    assert [
        item["finding_id"] for item in sort_findings(FINDINGS, "Severity")
    ] == ["HIGH-1", "LOW-1"]


def test_finding_detail_frames_preserve_recorded_evidence_and_entities():
    finding = FINDINGS[1]

    evidence = finding_evidence_frame(finding)
    entities = affected_entities_frame(finding)

    assert set(evidence["Evidence measure"]) == {
        "Threshold percentage",
        "Excluded reasons",
    }
    assert any(
        "missing dates" in str(value)
        for value in evidence["Recorded value"]
    )
    assert len(entities) == 3
    assert set(entities["Entity type"]) == {"Projects", "Resources"}


def test_supporting_evidence_is_narrowed_only_by_recorded_rule_id():
    evidence = pd.DataFrame([
        {"RuleID": "RULE-HIGH", "ProjectID": "P1"},
        {"RuleID": "OTHER", "ProjectID": "P2"},
    ])

    selected = filter_evidence_for_finding(evidence, FINDINGS[1])

    assert selected.to_dict("records") == [
        {"RuleID": "RULE-HIGH", "ProjectID": "P1"}
    ]


def test_finding_domain_maps_to_recorded_fitness_capability():
    assert capability_for_finding({"domain": "governance"}) == "portfolio"
    assert capability_for_finding({"domain": "schedule"}) == "schedule"
    assert capability_for_finding({"domain": "unknown"}) is None
