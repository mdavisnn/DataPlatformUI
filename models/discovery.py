from dataclasses import dataclass, field


@dataclass(frozen=True)
class Dataset:
    name: str
    source_file: str | None = None
    recognised_as: str | None = None
    row_count: int | None = None
    column_count: int | None = None
    missing_fields: list[str] = field(default_factory=list)
    unexpected_fields: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

