from __future__ import annotations

from fastapi.testclient import TestClient

from routemind_compute.api.app import app

client = TestClient(app)


def payload() -> dict[str, object]:
    return {
        "scenario_id": "scenario-1",
        "seed": 42,
        "configuration": [],
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
    assert {item["maturity"] for item in body} == {"BASELINE", "ENGINEERING"}


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
    changed_configuration["strategy"] = "weighted-greedy"
    changed_configuration["configuration"] = [["distance_weight", "2.0"]]
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


def test_parameter_schema_exposes_versioned_supported_weights() -> None:
    response = client.get("/api/v1/strategies/risk-aware/parameters")
    assert response.status_code == 200
    body = response.json()
    assert body["strategy"] == "risk-aware"
    assert body["version"] == "1.0.0"
    assert {item["key"] for item in body["parameters"]} == {
        "distance",
        "readiness",
        "overtime",
        "service_risk",
        "balance",
    }
    assert client.get("/api/v1/strategies/missing/parameters").status_code == 404


def test_routebench_experiment_records_manifest_and_output_provenance() -> None:
    response = client.post(
        "/api/v1/experiments/routebench",
        json={
            "manifest_id": "manifest-api-1",
            "code_version": "git:test",
            "scenario_id": "scenario-api-1",
            "seed": 7,
            "load_profile": "reduced",
            "city_state": "fixture",
            "dataset_provenance": "fixture:api",
            "strategies": ["nearest", "weighted-greedy"],
            "configuration": [["batch_size", "2"]],
            "parameter_configuration": [["distance_weight", "2.0"]],
            "demands": [
                {
                    "request_id": "request-api-1",
                    "pickup": {"latitude": 31.2304, "longitude": 121.4737},
                    "tick": 0,
                }
            ],
            "couriers": [
                {
                    "courier_id": "courier-api-1",
                    "location": {"latitude": 31.231, "longitude": 121.474},
                }
            ],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "experiment"
    assert len(body["manifest_digest"]) == 64
    assert len(body["output_digest"]) == 64
    assert [metric["strategy"] for metric in body["metrics"]] == [
        "nearest",
        "weighted-greedy",
    ]
    assert body["parameter_configuration"] == [["distance_weight", "2.0"]]


def shadow_payload() -> dict[str, object]:
    return {
        "manifest_id": "shadow-api-1",
        "code_version": "git:test",
        "scenario_id": "shadow-scenario-1",
        "seed": 11,
        "active_strategy": "nearest",
        "candidate_strategy": "risk-aware",
        "policy": {
            "minimum_samples": 1,
            "maximum_failure_rate": 0.0,
            "maximum_assignment_rate_drop": 0.0,
            "maximum_disagreement_rate": 0.0,
        },
        "problems": [
            {
                "request_id": "shadow-request-1",
                "pickup": {"latitude": 31.2304, "longitude": 121.4737},
                "candidates": [
                    {
                        "courier_id": "near-risky",
                        "location": {"latitude": 31.2305, "longitude": 121.4738},
                        "service_risk": 0.9,
                    },
                    {
                        "courier_id": "far-safe",
                        "location": {"latitude": 31.24, "longitude": 121.48},
                        "service_risk": 0.0,
                    },
                ],
            }
        ],
    }


def test_shadow_evaluation_exposes_hold_reasons_and_no_candidate_authority() -> None:
    response = client.post("/api/v1/shadow/evaluate", json=shadow_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "shadow"
    assert body["action"] == "hold"
    assert "disagreement_rate_exceeded" in body["reasons"]
    assert body["candidate_authority"] == "none"
    assert body["metrics"]["sample_count"] == 1
    assert body["observations"][0]["disagrees"] is True
    assert len(body["manifest_digest"]) == 64
    assert len(body["run_digest"]) == 64


def test_shadow_evaluation_rejects_same_strategy_and_unknown_candidate() -> None:
    same = shadow_payload()
    same["candidate_strategy"] = "nearest"
    assert client.post("/api/v1/shadow/evaluate", json=same).status_code == 422
    unknown = shadow_payload()
    unknown["candidate_strategy"] = "missing"
    assert client.post("/api/v1/shadow/evaluate", json=unknown).status_code == 400
