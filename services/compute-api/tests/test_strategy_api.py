from __future__ import annotations

from fastapi.testclient import TestClient

from routemind_compute.api.app import app

client = TestClient(app)


def payload() -> dict[str, object]:
    return {
        "scenario_id": "scenario-1",
        "seed": 42,
        "configuration": [["objective", "distance"], ["region", "east"]],
        "request_id": "request-1",
        "strategy": "nearest",
        "pickup": {"latitude": 31.2304, "longitude": 121.4737},
        "candidates": [
            {"courier_id": "courier-1", "location": {"latitude": 31.231, "longitude": 121.474}}
        ],
    }


def test_catalog_is_sorted_and_versioned() -> None:
    response = client.get("/api/v1/strategies")
    assert response.status_code == 200
    body = response.json()
    assert [item["name"] for item in body] == sorted(item["name"] for item in body)
    assert all(
        item["version"] and item["capabilities"] and item["status"] == "available" for item in body
    )


def test_execution_returns_stable_provenance_and_metrics() -> None:
    first = client.post("/api/v1/strategies/execute", json=payload())
    second = client.post("/api/v1/strategies/execute", json=payload())
    assert first.status_code == second.status_code == 200
    body = first.json()
    assert body["source"] == "experiment"
    assert body["selected_courier"] == "courier-1"
    assert body["metrics"]["candidate_count"] == 1
    assert body["metrics"]["eligible_candidate_count"] == 1
    assert body["provenance"]["input_digest"] == second.json()["provenance"]["input_digest"]
    assert body["provenance"]["output_digest"] == second.json()["provenance"]["output_digest"]


def test_execution_digest_changes_with_seed_and_configuration() -> None:
    changed_seed = payload()
    changed_seed["seed"] = 43
    changed_configuration = payload()
    changed_configuration["configuration"] = [["objective", "risk"]]
    digests = {
        client.post("/api/v1/strategies/execute", json=value).json()["provenance"]["input_digest"]
        for value in (payload(), changed_seed, changed_configuration)
    }
    assert len(digests) == 3


def test_execution_rejects_unknown_and_unbounded_inputs() -> None:
    unknown = payload()
    unknown["strategy"] = "missing"
    assert client.post("/api/v1/strategies/execute", json=unknown).status_code == 400
    unbounded = payload()
    unbounded["configuration"] = [[f"key-{index}", "value"] for index in range(33)]
    assert client.post("/api/v1/strategies/execute", json=unbounded).status_code == 422
