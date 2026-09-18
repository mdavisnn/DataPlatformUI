import streamlit as st

from components.header import render_header
from components.metric_card import render_metrics
from components.status_badge import render_status_badge
from services.page_context import selected_run


settings, run = selected_run()
render_header("Overview", run.engagement_name or run.run_id)
render_status_badge(run.status)
render_metrics([("Files", run.source_file_count), ("Records", run.record_count), ("Failed stage", run.failed_stage)])

st.subheader("Pipeline journey")
if run.stages:
    for stage, status in run.stages.items():
        icon = "✅" if status.lower() in {"success", "completed", "pass", "passed"} else "⚠️" if status.lower() in {"failed", "fail", "error"} else "➖"
        st.write(f"{icon} **{stage.replace('_', ' ').title()}** — {status.replace('_', ' ').title()}")
else:
    st.info("Stage status metadata is not available for this run.")

