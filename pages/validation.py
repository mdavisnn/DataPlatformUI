import streamlit as st

from components.header import render_header
from services.page_context import selected_run
from services.validation_reader import load_validation
from services.output_reader import load_validation_errors


settings, run = selected_run()
render_header("Validation", "Where the data does not meet expected rules")
data = load_validation(settings, run.run_id)
errors = load_validation_errors(settings, run.run_id)
if not data:
    st.info("No validation metadata is available for this run.")
else:
    with st.container(horizontal=True):
        st.metric("Quality", data.get("quality_status", "Unknown"), border=True)
        st.metric("Errors", data.get("total_errors", 0), border=True)
        st.metric("Warnings", data.get("total_warnings", 0), border=True)
    datasets = data.get("datasets", {})
    if isinstance(datasets, dict) and datasets:
        rows = [{"dataset": name, **details} for name, details in datasets.items() if isinstance(details, dict)]
        st.dataframe(rows, hide_index=True, key="validation_datasets")
    if errors and errors.data is not None and errors.path is not None:
        st.subheader("Failing records")
        st.dataframe(errors.data, hide_index=True, key="validation_errors")
        st.download_button(
            "Download validation errors", data=errors.path.read_bytes(),
            file_name=errors.name, mime="text/csv", icon=":material/download:",
        )
    elif data.get("total_errors", 0):
        st.warning("Validation errors were reported, but validation_errors.csv is unavailable.")
    else:
        st.success("No failing records were reported.")
    with st.expander("Validation evidence"):
        st.json(data, expanded=False)
