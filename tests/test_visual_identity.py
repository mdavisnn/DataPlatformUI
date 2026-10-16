from pathlib import Path
import tomllib

import pandas as pd

from components.diagnostic_charts import severity_distribution_chart


ROOT = Path(__file__).parents[1]


def test_streamlit_theme_defines_data_lab_visual_foundation():
    with (ROOT / ".streamlit" / "config.toml").open("rb") as handle:
        config = tomllib.load(handle)

    theme = config["theme"]
    sidebar = theme["sidebar"]

    assert theme["primaryColor"] == "#5cc39d"
    assert theme["linkColor"] == "#0f766e"
    assert theme["textColor"] == "#10213d"
    assert theme["baseRadius"] == "8px"
    assert theme["showWidgetBorder"] is True
    assert len(theme["chartCategoricalColors"]) >= 7
    assert len(theme["chartSequentialColors"]) == 10
    assert sidebar["backgroundColor"] == "#0a2342"
    assert sidebar["textColor"] == "#e9f0f7"
    assert sidebar["primaryColor"] == "#5cc39d"


def test_visual_identity_has_one_global_theme_source():
    assert not (ROOT / "assets" / "styles.css").exists()


def test_severity_chart_reserves_amber_for_medium_conditions():
    chart = severity_distribution_chart(pd.DataFrame([
        {"Severity": "High", "Findings": 1},
        {"Severity": "Medium", "Findings": 2},
        {"Severity": "Low", "Findings": 3},
    ]))

    scale = chart.to_dict()["encoding"]["color"]["scale"]

    assert scale["domain"] == ["High", "Medium", "Low"]
    assert scale["range"] == ["#dc2626", "#d97706", "#64748b"]
