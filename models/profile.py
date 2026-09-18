from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProfileResult:
    dataset: str
    row_count: int | None = None
    completeness: float | None = None
    duplicate_identifiers: int | None = None
    field_metrics: list[dict] = field(default_factory=list)

