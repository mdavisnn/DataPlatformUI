from dataclasses import dataclass, field


@dataclass(frozen=True)
class StageResult:
    stage: str
    status: str
    summary: dict = field(default_factory=dict)
    findings: list[dict] = field(default_factory=list)
    artifacts: list[dict] = field(default_factory=list)


@dataclass(frozen=True)
class Metric:
    label: str
    value: str | int | float
    help_text: str | None = None


@dataclass(frozen=True)
class WorkshopObservation:
    severity: str
    title: str
    evidence: str
    next_step: str | None = None

