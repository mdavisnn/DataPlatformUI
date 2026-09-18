from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationFinding:
    rule_id: str
    title: str
    severity: str = "unknown"
    affected_records: int | None = None
    dataset: str | None = None
    field: str | None = None
    explanation: str | None = None
    next_step: str | None = None

