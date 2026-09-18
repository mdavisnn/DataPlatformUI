from __future__ import annotations

import streamlit as st

from services.output_reader import TabularOutput


def render_tabular_output(output: TabularOutput, *, key_prefix: str) -> None:
    with st.container(border=True):
        st.subheader(output.title)
        if output.description:
            st.caption(output.description)
        if not output.available:
            st.info(f"{output.name} has not been produced.")
            return
        assert output.data is not None and output.path is not None
        with st.container(horizontal=True):
            st.metric("Rows", f"{len(output.data):,}", border=True)
            st.metric("Columns", len(output.data.columns), border=True)
        st.dataframe(output.data, hide_index=True, key=f"{key_prefix}_{output.name}")
        st.download_button(
            "Download CSV", data=output.path.read_bytes(), file_name=output.name,
            mime="text/csv", icon=":material/download:",
            key=f"{key_prefix}_download_{output.name}",
        )
