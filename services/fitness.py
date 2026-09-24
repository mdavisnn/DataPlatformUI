"""Present stored fitness assessments in consultant-friendly language."""

from __future__ import annotations

import pandas as pd


FITNESS_RULES = {
    "FIT-MISSING-DATASET": (
        "Required dataset is absent",
        "A whole evidence set needed by this analysis is missing, so "
        "dependent results cannot be produced reliably.",
    ),
    "FIT-REQUIRED-FIELD": (
        "Required field is missing",
        "This field is essential for identifying or connecting the evidence, "
        "so analysis that depends on it may be unavailable.",
    ),
    "FIT-OPTIONAL-FIELD": (
        "Optional field is incomplete",
        "This information is useful but not essential, so analysis can "
        "continue although some results may have less context.",
    ),
    "FIT-DUPLICATE-ID": (
        "Identifier is not unique",
        "More than one record uses the same identifier, so the platform "
        "cannot safely tell those records apart.",
    ),
    "FIT-BROKEN-RELATIONSHIP": (
        "Related record cannot be found",
        "A reference points to evidence that is not present, so those records "
        "cannot be connected reliably.",
    ),
    "FIT-UNUSABLE-DATE": (
        "Date cannot be read",
        "A date is present but is not in a supported form, so date-based "
        "analysis cannot use that value.",
    ),
    "FIT-DATE-SEQUENCE": (
        "Dates are in an unexpected order",
        "The recorded start and finish order is unusual and should be checked "
        "before drawing schedule conclusions.",
    ),
    "FIT-INVALID-ALLOCATION": (
        "Allocation value is outside the expected range",
        "The planned allocation is not a usable percentage, so resource "
        "pressure results may be limited.",
    ),
}

DETAIL_COLUMNS = [
    "Rule",
    "Dataset",
    "Field",
    "Occurrences",
    "What this means",
    "Rule ID",
]


def _fallback_rule(rule_id: str) -> tuple[str, str]:
    return FITNESS_RULES.get(
        rule_id,
        (
            rule_id.replace("-", " ").title(),
            "This recorded condition may limit analysis that depends on the "
            "affected evidence.",
        ),
    )


def capability_condition_frame(
    assessment: dict,
    key: str,
    evidence: pd.DataFrame,
) -> pd.DataFrame:
    """Expand capability summaries to field-level explanatory rows."""

    rows = []
    for item in assessment.get(key, []):
        rule_id = str(item.get("rule_id", ""))
        dataset = str(item.get("dataset", ""))
        title, explanation = _fallback_rule(rule_id)
        title = str(item.get("rule_title") or title)
        explanation = str(item.get("explanation") or explanation)
        item_field = item.get("field")
        if item_field is not None:
            groups = [(str(item_field), int(item.get("count", 0)))]
        else:
            matches = evidence
            if not matches.empty:
                matches = matches[
                    (matches["rule_id"].astype(str) == rule_id)
                    & (matches["dataset"].astype(str) == dataset)
                ]
            if matches.empty or "field" not in matches:
                groups = [("", int(item.get("count", 0)))]
            else:
                fields = matches["field"].fillna("").astype(str)
                groups = [
                    (field, int(count))
                    for field, count in fields.value_counts(
                        dropna=False
                    ).items()
                ]
        for field, count in groups:
            rows.append({
                "Rule": title,
                "Dataset": dataset,
                "Field": field or "Whole dataset",
                "Occurrences": count,
                "What this means": explanation,
                "Rule ID": rule_id,
            })
    return pd.DataFrame(rows, columns=DETAIL_COLUMNS)


def missing_dataset_frame(assessment: dict) -> pd.DataFrame:
    """Explain capability datasets which are entirely unavailable."""

    rows = [
        {
            "Dataset": dataset,
            "What this means": (
                "This capability expects this evidence set. Analysis that "
                "depends on it cannot run reliably until it is supplied."
            ),
        }
        for dataset in assessment.get("missing_datasets", [])
    ]
    return pd.DataFrame(rows, columns=["Dataset", "What this means"])


def unavailable_rule_frame(assessment: dict) -> pd.DataFrame:
    """Explain analyses suppressed by unavailable or unusable evidence."""

    rows = []
    for item in assessment.get("unavailable_rules", []):
        rule_id = str(item.get("rule_id", ""))
        fallback_title, _ = _fallback_rule(rule_id)
        datasets = item.get("unfit_datasets", [])
        rows.append({
            "Analysis": item.get("rule_title") or fallback_title,
            "Unavailable evidence": ", ".join(map(str, datasets)),
            "What this means": item.get("explanation") or (
                "This analysis was not run because evidence it requires is "
                "missing or structurally unusable."
            ),
            "Rule ID": rule_id,
        })
    return pd.DataFrame(
        rows,
        columns=[
            "Analysis",
            "Unavailable evidence",
            "What this means",
            "Rule ID",
        ],
    )
