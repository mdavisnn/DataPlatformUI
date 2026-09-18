import json

from config.settings import Settings
from services.discovery_reader import load_discovery


def test_uses_sources_as_discovery_fallback(tmp_path):
    run_path = tmp_path / "metadata" / "runs" / "demo"
    run_path.mkdir(parents=True)
    (run_path / "sources.json").write_text(json.dumps({"datasets": ["projects"]}), encoding="utf-8")
    assert load_discovery(Settings(tmp_path), "demo") == {"datasets": ["projects"]}

