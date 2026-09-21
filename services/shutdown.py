"""Graceful shutdown support for the local Streamlit server."""

from __future__ import annotations

import signal
from typing import Final


class ShutdownUnavailable(RuntimeError):
    """Raised when the app is not running under Streamlit's CLI server."""


_UNAVAILABLE_HANDLERS: Final = {
    None,
    signal.SIG_DFL,
    signal.SIG_IGN,
    signal.default_int_handler,
}


def request_streamlit_shutdown() -> None:
    """Invoke Streamlit's registered SIGINT handler for graceful cleanup."""

    if signal.getsignal(signal.SIGINT) in _UNAVAILABLE_HANDLERS:
        raise ShutdownUnavailable(
            "The Streamlit server shutdown handler is not active. "
            "Stop the server from its terminal with Ctrl+C."
        )
    signal.raise_signal(signal.SIGINT)
