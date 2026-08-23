from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from routemind_compute.api.app import app
from routemind_compute.application.clock import (
    REPLAY_CLOCK,
    SIMULATED_CLOCK,
    WALL_CLOCK,
    validate_clock_domain,
)


def test_clock_domain_contract_is_explicit_and_rejects_unknown_values() -> None:
    validate_clock_domain(SIMULATED_CLOCK, allowed=(SIMULATED_CLOCK, REPLAY_CLOCK))
    validate_clock_domain(REPLAY_CLOCK, allowed=(SIMULATED_CLOCK, REPLAY_CLOCK))
    with pytest.raises(ValueError, match="clock domain"):
        validate_clock_domain(WALL_CLOCK, allowed=(SIMULATED_CLOCK, REPLAY_CLOCK))


def test_api_exposes_wall_and_simulated_clock_domains() -> None:
    client = TestClient(app)
    live = client.post(
        "/api/v1/dispatch/snapshot",
        json={
            "request_id": "clock-live-1",
            "pickup": {"latitude": 31.23, "longitude": 121.47},
            "candidates": [],
        },
    )
    twin = client.get("/api/v1/twin/state")

    assert live.status_code == 200
    assert live.json()["clock_domain"] == WALL_CLOCK
    assert twin.status_code == 200
    assert twin.json()["clock_domain"] == SIMULATED_CLOCK
