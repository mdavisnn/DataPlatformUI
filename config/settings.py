from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


class SettingsError(RuntimeError):
    """Raised when the local DataPlatform path is unavailable."""

    pass


@dataclass(frozen=True)
class Settings:
    platform_path: Path

    @classmethod
    def from_environment(cls) -> "Settings":
        load_dotenv()
        raw_path = os.getenv("DATALAB_PLATFORM_PATH")
        if not raw_path:
            raise SettingsError("DATALAB_PLATFORM_PATH is not configured.")
        platform_path = Path(raw_path).expanduser().resolve()
        if not platform_path.is_dir():
            raise SettingsError(f"The configured platform path does not exist: {platform_path}")
        return cls(platform_path)

    @property
    def runs_path(self) -> Path:
        candidates = (
            self.platform_path / "local-data" / "metadata" / "runs",
            self.platform_path / "metadata" / "runs",
        )
        return next((path for path in candidates if path.is_dir()), candidates[0])

    def data_path(self, area: str) -> Path:
        """Return the local directory for a governed data area."""
        candidates = (
            self.storage_root / area,
            self.platform_path / area,
        )
        return next((path for path in candidates if path.is_dir()), candidates[0])

    @property
    def storage_root(self) -> Path:
        configured = os.getenv("DATA_PLATFORM_STORAGE_ROOT")
        if configured:
            path = Path(configured).expanduser()
            if not path.is_absolute():
                path = self.platform_path / path
            return path.resolve()
        return (self.platform_path / "local-data").resolve()

    @property
    def metadata_path(self) -> Path:
        return self.data_path("metadata")

    @property
    def raw_path(self) -> Path:
        return self.data_path("raw")

    @property
    def processed_path(self) -> Path:
        return self.data_path("processed")

    @property
    def curated_path(self) -> Path:
        return self.data_path("curated")

    @property
    def snapshots_path(self) -> Path:
        candidates = (
            self.metadata_path / "snapshots",
            self.platform_path / "metadata" / "snapshots",
        )
        return next((path for path in candidates if path.is_dir()), candidates[0])
