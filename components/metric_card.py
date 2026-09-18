import streamlit as st


def render_metrics(metrics: list[tuple[str, object]]) -> None:
    if not metrics:
        return
    columns = st.columns(len(metrics))
    for column, (label, value) in zip(columns, metrics):
        column.metric(label, "—" if value is None else value)

