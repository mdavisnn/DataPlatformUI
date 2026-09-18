import pandas as pd
import plotly.express as px


def completeness_chart(rows: list[dict]):
    frame = pd.DataFrame(rows)
    if frame.empty or not {"field", "completeness"}.issubset(frame.columns):
        return None
    return px.bar(frame, x="completeness", y="field", orientation="h", range_x=[0, 100])

