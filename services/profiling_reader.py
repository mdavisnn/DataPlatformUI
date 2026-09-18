from config.settings import Settings
from services.platform_reader import optional_json


def load_profiling(settings: Settings, run_id: str) -> dict:
    return optional_json(settings.runs_path / run_id / "profiling.json") or {}

