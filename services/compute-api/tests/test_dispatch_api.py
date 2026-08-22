from fastapi.testclient import TestClient

from routemind_compute.api.app import app

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
