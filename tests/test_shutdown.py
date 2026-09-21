import signal

import pytest

from services.shutdown import ShutdownUnavailable, request_streamlit_shutdown


def test_request_streamlit_shutdown_raises_sigint(monkeypatch):
    sent_signals = []
    monkeypatch.setattr(signal, "getsignal", lambda _: object())
    monkeypatch.setattr(signal, "raise_signal", sent_signals.append)

    request_streamlit_shutdown()

    assert sent_signals == [signal.SIGINT]


def test_request_streamlit_shutdown_requires_server_handler(monkeypatch):
    monkeypatch.setattr(
        signal,
        "getsignal",
        lambda _: signal.default_int_handler,
    )

    with pytest.raises(ShutdownUnavailable, match="Ctrl.C"):
        request_streamlit_shutdown()
