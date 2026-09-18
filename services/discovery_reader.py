from config.settings import Settings
from services.platform_reader import optional_json


def load_discovery(settings: Settings, run_id: str) -> dict:
    run_path = settings.runs_path / run_id
    return optional_json(run_path / "discovery.json") or optional_json(run_path / "sources.json") or {}

