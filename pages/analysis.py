import streamlit as st

from components.header import render_header
from components.output_viewer import render_tabular_output
from services.output_reader import load_analysis_outputs
from services.page_context import selected_run


settings, run = selected_run()
render_header("Analysis", "Point-in-time, historical, and data-quality outputs")
st.info(
    "Analysis runs separately from the governed run. Point-in-time files describe the "
    "latest curated snapshot; history files can combine multiple runs."
)

outputs = load_analysis_outputs(settings)
groups = list(dict.fromkeys(output.group for output in outputs))
group = st.segmented_control("Analysis stage", groups, default=groups[0], key="analysis_group")
for output in outputs:
    if output.group == group:
        render_tabular_output(output, key_prefix="analysis")
