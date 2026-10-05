from pathlib import Path
import tomllib


ROOT = Path(__file__).parents[1]


def test_streamlit_theme_defines_data_lab_visual_foundation():
    with (ROOT / ".streamlit" / "config.toml").open("rb") as handle:
        config = tomllib.load(handle)

    theme = config["theme"]
    sidebar = theme["sidebar"]

    assert theme["primaryColor"] == "#c2410c"
    assert theme["textColor"] == "#10213d"
    assert theme["baseRadius"] == "8px"
    assert theme["showWidgetBorder"] is True
    assert len(theme["chartCategoricalColors"]) >= 7
    assert len(theme["chartSequentialColors"]) == 10
    assert sidebar["backgroundColor"] == "#0a2342"
    assert sidebar["textColor"] == "#e9f0f7"


def test_visual_identity_has_one_global_theme_source():
    assert not (ROOT / "assets" / "styles.css").exists()
