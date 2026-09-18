import streamlit as st

from components.header import render_header
from components.output_viewer import render_tabular_output
from services.output_reader import load_processed_outputs, load_processing
from services.page_context import selected_run


settings, run = selected_run()
render_header("Processing", "The standardised datasets produced by this governed run")
metadata = load_processing(settings, run.run_id)
outputs = load_processed_outputs(settings, run.run_id)

if not outputs:
    st.info("No processing outputs are available for this run.")
else:
    for output in outputs:
        render_tabular_output(output, key_prefix="processed")

with st.expander("Processing evidence"):
    st.json(metadata, expanded=False)
