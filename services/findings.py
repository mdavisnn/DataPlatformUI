"""Presentation-only transformations for governed diagnostic Findings."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pandas as pd


SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}

_CAPABILITY_BY_DOMAIN = {
    "data": "data",
    "dependency": "dependency",
    "exploratory": "exploratory",
    "governance": "portfolio",
    "portfolio": "portfolio",
    "reporting": "reporting",
    "resource": "resource",
    "schedule": "schedule",
}


def affected_entity_count(finding: dict[str, Any]) -> int:
    """Return the number of governed entity references on a Finding."""

    return sum(
        len(values)
        for values in finding.get("affected_entities", {}).values()
        if isinstance(values, list)
    )


def filter_findings(
    findings: Iterable[dict[str, Any]],
    *,
    domains: Iterable[str] = (),
    severities: Iterable[str] = (),
) -> list[dict[str, Any]]:
    """Narrow Findings by their persisted domain and severity values."""

    domain_values = {str(value).lower() for value in domains}
    severity_values = {str(value).lower() for value in severities}
    return [
        finding
        for finding in findings
        if (
            not domain_values
            or str(finding.get("domain", "")).lower() in domain_values
        )
        and (
            not severity_values
            or str(finding.get("severity", "")).lower()
            in severity_values
        )
    ]


def sort_findings(
    findings: Iterable[dict[str, Any]], sort_by: str,
) -> list[dict[str, Any]]:
    """Order Findings for review without changing their diagnostic meaning."""

    rows = list(findings)
    if sort_by == "Domain":
        key = lambda item: (
            str(item.get("domain", "")),
            SEVERITY_ORDER.get(str(item.get("severity", "")).lower(), 9),
            str(item.get("title", "")),
        )
    elif sort_by == "Title":
        key = lambda item: (
            str(item.get("title", "")),
            str(item.get("finding_id", "")),
        )
    else:
        key = lambda item: (
            SEVERITY_ORDER.get(str(item.get("severity", "")).lower(), 9),
            str(item.get("domain", "")),
            str(item.get("title", "")),
        )
    return sorted(rows, key=key)


def finding_review_frame(findings: Iterable[dict[str, Any]]) -> pd.DataFrame:
    """Create the compact selectable Finding index shown in the UI."""

    return pd.DataFrame([
        {
            "Severity": str(finding.get("severity", "unknown")).title(),
            "Title": finding.get("title", "Untitled finding"),
            "Domain": str(finding.get("domain", "unknown")).title(),
            "Rule": finding.get("rule_id", "Not recorded"),
            "Affected": affected_entity_count(finding),
        }
        for finding in findings
    ])


def finding_evidence_frame(finding: dict[str, Any]) -> pd.DataFrame:
    """Present the Finding's persisted evidence facts as readable rows."""

    rows = []
    for key, value in finding.get("evidence", {}).items():
        if isinstance(value, list):
            display = ", ".join(map(str, value)) or "None recorded"
        elif isinstance(value, dict):
            display = ", ".join(
                f"{nested_key}: {nested_value}"
                for nested_key, nested_value in value.items()
            ) or "None recorded"
        elif value is None:
            display = "Not available"
        else:
            display = value
        rows.append({
            "Evidence measure": key.replace("_", " ").capitalize(),
            "Recorded value": display,
        })
    return pd.DataFrame(rows)


def affected_entities_frame(finding: dict[str, Any]) -> pd.DataFrame:
    """Expand affected entity references into one row per governed ID."""

    return pd.DataFrame([
        {
            "Entity type": entity_type.replace("_", " ").title(),
            "Entity ID": str(entity_id),
        }
        for entity_type, values in finding.get(
            "affected_entities", {}
        ).items()
        for entity_id in values
    ])


def filter_evidence_for_finding(
    evidence: pd.DataFrame, finding: dict[str, Any],
) -> pd.DataFrame:
    """Use a persisted rule column to isolate a Finding's artifact rows."""

    for column in ("RuleID", "rule_id"):
        if column in evidence.columns:
            return evidence.loc[
                evidence[column].astype(str)
                == str(finding.get("rule_id", ""))
            ].copy()
    return evidence.copy()


def capability_for_finding(finding: dict[str, Any]) -> str | None:
    """Map a Finding domain to the corresponding persisted fitness capability."""

    return _CAPABILITY_BY_DOMAIN.get(
        str(finding.get("domain", "")).lower()
    )
