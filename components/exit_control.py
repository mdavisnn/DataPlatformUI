"""Global control for stopping the local consultant console."""

import streamlit as st

from services.shutdown import ShutdownUnavailable, request_streamlit_shutdown


def render_exit_control() -> None:
    """Render a sidebar button that requests graceful server shutdown."""

    if not st.button(
        "Exit Data Lab",
        key="exit_application",
        help="Stop the local Streamlit server and return control to the terminal.",
        icon=":material/power_settings_new:",
        type="tertiary",
        width="stretch",
    ):
        return

    try:
        request_streamlit_shutdown()
    except ShutdownUnavailable as error:
        st.error(str(error), icon=":material/error:")
        return
    st.stop()
