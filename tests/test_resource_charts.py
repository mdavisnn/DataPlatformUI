import pandas as pd

from components.resource_charts import allocation_pressure_chart


def test_allocation_pressure_uses_resource_id_in_duplicate_name_lanes():
    pressure = pd.DataFrame([
        {
            "ResourceName": "Ben Green",
            "ResourceID": "R014",
            "PeakConcurrentAllocationPct": 175,
            "ProjectCount": 3,
            "ConflictPeriodCount": 4,
        },
        {
            "ResourceName": "Ben Green",
            "ResourceID": "R020",
            "PeakConcurrentAllocationPct": 150,
            "ProjectCount": 2,
            "ConflictPeriodCount": 3,
        },
    ])

    specification = allocation_pressure_chart(pressure, 100).to_dict()

    bar_encoding = specification["layer"][0]["encoding"]
    assert bar_encoding["y"]["field"] == "ResourceLabel"
    assert {
        tooltip["field"] for tooltip in bar_encoding["tooltip"]
    } >= {"ResourceName", "ResourceID"}
    chart_rows = next(
        rows for rows in specification["datasets"].values()
        if rows and "ResourceLabel" in rows[0]
    )
    assert {row["ResourceLabel"] for row in chart_rows} == {
        "Ben Green \u00b7 R014",
        "Ben Green \u00b7 R020",
    }
