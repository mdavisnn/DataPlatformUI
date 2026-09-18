from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class PipelineRun:
    run_id: str
    status: str = "unknown"
    started_at: str | None = None
    completed_at: str | None = None
    failed_stage: str | None = None
    engagement_name: str | None = None
    stages: dict[str, str] = field(default_factory=dict)
    source_file_count: int | None = None
    record_count: int | None = None

    @property
    def sort_time(self) -> datetime:
        for value in (self.started_at, self.completed_at):
            if value:
                try:
                    return datetime.fromisoformat(value.replace("Z", "+00:00"))
                except ValueError:
                    pass
        return datetime.min

