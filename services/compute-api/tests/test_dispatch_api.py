import pytest
from fastapi.testclient import TestClient

import routemind_compute.api.app as app_module
from routemind_compute.application.registry import StrategyRegistry
from routemind_compute.domain.dispatch import DispatchDecision, DispatchProblem

app = app_module.app

client = TestClient(app)


def test_dispatch_snapshot_is_live_and_uses_registry() -> None:
    response = client.post(
        "/api/v1/dispatch/snapshot",
        json={
            "request_id": "ops-live-1",
            "strategy": "nearest",
            "pickup": {"latitude": 31.2304, "longitude": 121.4737},
            "candidates": [
                {"courier_id": "courier-2", "location": {"latitude": 31.24, "longitude": 121.48}},
                {"courier_id": "courier-1", "location": {"latitude": 31.231, "longitude": 121.474}},
            ],
        },
        headers={"X-Trace-Id": "0123456789abcdef0123456789abcdef"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "live"
    assert body["selected_courier"] == "courier-1"
    assert body["trace_id"] == "0123456789abcdef0123456789abcdef"
    assert any(item[0] == "candidate_count" for item in body["metadata"])
    metadata = dict(body["metadata"])
    assert metadata["travel_provider"] == "deterministic-local"
    assert metadata["travel_candidate_count"] == "2"
    assert metadata["travel_fallback_used"] == "false"
    assert float(metadata["selected_travel_seconds"]) > 0


def test_dispatch_snapshot_rejects_unknown_strategy_and_duplicate_candidates() -> None:
    unknown = client.post(
        "/api/v1/dispatch/snapshot",
        json={
            "request_id": "ops-live-2",
            "strategy": "not-registered",
            "pickup": {"latitude": 0, "longitude": 0},
            "candidates": [],
        },
    )
    duplicate = client.post(
        "/api/v1/dispatch/snapshot",
        json={
            "request_id": "ops-live-3",
            "pickup": {"latitude": 0, "longitude": 0},
            "candidates": [
                {"courier_id": "same", "location": {"latitude": 0, "longitude": 0}},
                {"courier_id": "same", "location": {"latitude": 1, "longitude": 1}},
            ],
        },
    )

    assert unknown.status_code == 400
    assert duplicate.status_code == 400


def test_dispatch_snapshot_exposes_explicit_strategy_failure_fallback_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BrokenStrategy:
        name = "broken"
        version = "9.9.9"

        def solve(self, problem: DispatchProblem) -> DispatchDecision:
            raise RuntimeError("injected strategy failure")

    monkeypatch.setattr(app_module, "REGISTRY", StrategyRegistry((BrokenStrategy(),)))
    response = client.post(
        "/api/v1/dispatch/snapshot",
        json={
            "request_id": "ops-failure-1",
            "strategy": "broken",
            "pickup": {"latitude": 0, "longitude": 0},
            "candidates": [],
        },
        headers={"X-Trace-Id": "trace-failure-1"},
    )

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["code"] == "strategy_unavailable"
    assert detail["trace_id"] == "trace-failure-1"
    assert detail["metadata"] == {
        "fallback_strategy": "nearest",
        "fallback_available": "true",
        "failure_type": "RuntimeError",
    }


def test_dispatch_snapshot_applies_constraints_and_exposes_infeasibility_metadata() -> None:
    response = client.post(
        "/api/v1/dispatch/snapshot",
        json={
            "request_id": "ops-constraints-1",
            "strategy": "nearest",
            "pickup": {"latitude": 31.2304, "longitude": 121.4737},
            "demand_units": 2,
            "service_seconds": 10,
            "delivery_window": {"start_seconds": 0, "end_seconds": 60},
            "candidates": [
                {
                    "courier_id": "offline",
                    "location": {"latitude": 31.2304, "longitude": 121.4737},
                    "state": "offline",
                },
                {
                    "courier_id": "eligible",
                    "location": {"latitude": 31.24, "longitude": 121.48},
                    "capacity_units": 4,
                    "estimated_travel_seconds": 20,
                },
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["selected_courier"] == "eligible"
    metadata = dict(body["metadata"])
    assert metadata["eligible_candidate_count"] == "1"

    blocked = client.post(
        "/api/v1/dispatch/snapshot",
        json={
            "request_id": "ops-constraints-2",
            "strategy": "nearest",
            "pickup": {"latitude": 0, "longitude": 0},
            "demand_units": 3,
            "candidates": [
                {
                    "courier_id": "small",
                    "location": {"latitude": 0, "longitude": 0},
                    "capacity_units": 2,
                }
            ],
        },
    )

    assert blocked.status_code == 200
    blocked_body = blocked.json()
    assert blocked_body["selected_courier"] is None
    assert "small:capacity_insufficient=2.000" in blocked_body["rationale"]
    assert dict(blocked_body["metadata"])["eligible_candidate_count"] == "0"
