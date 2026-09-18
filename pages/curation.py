import streamlit as st

from components.header import render_header
from components.output_viewer import render_tabular_output
from services.output_reader import load_curation_outputs, load_snapshots
from services.page_context import selected_run


settings, run = selected_run()
render_header("Curation", "Business-facing datasets created by this governed run")
outputs = load_curation_outputs(settings, run.run_id)

if not outputs:
    st.info("No curated outputs are available for this run.")
else:
    for output in outputs:
        render_tabular_output(output, key_prefix="curated")

snapshots = load_snapshots(settings, run.run_id)
with st.expander("Dataset lineage"):
    if snapshots:
        dataset = st.selectbox("Dataset", list(snapshots), key="curation_snapshot")
        st.json(snapshots[dataset], expanded=False)
    else:
        st.info("No snapshot lineage is available for this run.")
