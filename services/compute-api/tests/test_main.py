from __future__ import annotations

from unittest.mock import patch

import pytest

from routemind_compute.__main__ import main


def test_main_uses_the_configured_loopback_port(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPUTE_API_PORT", "19081")

    with patch("routemind_compute.__main__.uvicorn.run") as run:
        main()

    run.assert_called_once_with(
        "routemind_compute.api.app:app",
        host="127.0.0.1",
        port=19081,
    )


def test_main_defaults_to_the_repository_port(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("COMPUTE_API_PORT", raising=False)

    with patch("routemind_compute.__main__.uvicorn.run") as run:
        main()

    run.assert_called_once_with(
        "routemind_compute.api.app:app",
        host="127.0.0.1",
        port=18081,
    )
