from fastapi.testclient import TestClient

from routemind_compute.api.app import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "UP"}


def test_request_context_is_echoed_and_metrics_are_exposed() -> None:
    response = client.get(
        "/healthz",
        headers={"X-Request-Id": "ops-42", "X-Trace-Id": "0123456789abcdef0123456789abcdef"},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-Id"] == "ops-42"
    assert response.headers["X-Trace-Id"] == "0123456789abcdef0123456789abcdef"

    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert "routemind_http_requests_total" in metrics.text


def test_bounded_request_burst_remains_healthy() -> None:
    responses = [client.get("/healthz") for _ in range(100)]

    assert all(response.status_code == 200 for response in responses)
    metrics = client.get("/metrics")
    assert (
        'routemind_http_requests_total{method="GET",service="compute-api",status="200"}'
        in metrics.text
    )


def test_system_info_declares_non_ownership_of_durable_state() -> None:
    response = client.get("/api/v1/system")

    assert response.status_code == 200
    assert response.json() == {
        "service": "compute-api",
        "runtime": "python",
        "architecture_version": "v1",
        "durable_state_owner": False,
    }


def test_location_integrity_exposes_signals_and_privacy_bounded_hotspots() -> None:
    observations = [
        {
            "courier_id": f"courier-{index}",
            "location": {"latitude": 31.2, "longitude": 121.4},
            "sequence": 1,
            "observed_at": "2026-08-24T00:00:00Z",
            "ingested_at": "2026-08-24T00:00:00Z",
        }
        for index in range(3)
    ]
    observations.append(
        {
            "courier_id": "courier-0",
            "location": {"latitude": 32.2, "longitude": 121.4},
            "sequence": 2,
            "observed_at": "2026-08-24T00:00:01Z",
            "ingested_at": "2026-08-24T00:00:01Z",
        }
    )
    response = client.post(
        "/api/v1/locations/integrity",
        json={"observations": observations, "reference_time": "2026-08-24T00:00:01Z"},
        headers={"X-Trace-Id": "location-integrity-trace"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["claim_label"] == "operational signal; not a disciplinary action"
    assert body["trace_id"] == "location-integrity-trace"
    assert body["assessments"][-1]["status"] == "SUSPECT"
    assert body["assessments"][-1]["signals"][0]["code"] == "impossible_speed"
    assert body["hotspots"][0]["unique_courier_count"] == 3
    assert all("courier_ids" not in cell for cell in body["hotspots"])


def test_location_integrity_rejects_timezone_less_observations() -> None:
    response = client.post(
        "/api/v1/locations/integrity",
        json={
            "observations": [
                {
                    "courier_id": "courier-1",
                    "location": {"latitude": 31.2, "longitude": 121.4},
                    "sequence": 1,
                    "observed_at": "2026-08-24T00:00:00",
                    "ingested_at": "2026-08-24T00:00:00Z",
                }
            ]
        },
    )

    assert response.status_code == 422


def test_eta_predict_returns_components_lineage_and_actual_outcome() -> None:
    response = client.post(
        "/api/v1/eta/predict",
        json={
            "order_id": "order-eta-1",
            "courier_id": "courier-1",
            "prediction_time": "2026-08-24T01:00:00Z",
            "courier_location": {"latitude": 31.2, "longitude": 121.4},
            "pickup_location": {"latitude": 31.21, "longitude": 121.41},
            "delivery_location": {"latitude": 31.22, "longitude": 121.42},
            "courier_available_at": "2026-08-24T01:00:00Z",
            "pickup_ready_at": "2026-08-24T01:01:00Z",
            "preparation_seconds": 120,
            "pickup_seconds": 30,
            "delivery_seconds": 20,
            "actual_delivered_at": "2026-08-24T01:15:00Z",
        },
        headers={"X-Trace-Id": "eta-trace"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["claim_label"] == "deterministic baseline; not calibrated production accuracy"
    assert body["trace_id"] == "eta-trace"
    assert [item["name"] for item in body["components"]] == [
        "dispatch",
        "travel",
        "preparation",
        "pickup",
        "delivery",
    ]
    assert body["outcome_available"] is True
    assert body["actual_duration_seconds"] == 900
    assert len(body["input_digest"]) == 64


def test_eta_predict_keeps_missing_preparation_explicit() -> None:
    response = client.post(
        "/api/v1/eta/predict",
        json={
            "order_id": "order-eta-2",
            "courier_id": "courier-1",
            "prediction_time": "2026-08-24T01:00:00Z",
            "courier_location": {"latitude": 31.2, "longitude": 121.4},
            "pickup_location": {"latitude": 31.21, "longitude": 121.41},
            "delivery_location": {"latitude": 31.22, "longitude": 121.42},
            "courier_available_at": "2026-08-24T01:00:00Z",
            "pickup_ready_at": "2026-08-24T01:01:00Z",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["predicted_delivery_at"] is None
    assert body["components"][2] == {
        "name": "preparation",
        "seconds": None,
        "source": "merchant preparation",
        "available": False,
    }


def test_eta_calibration_returns_metrics_and_gates_customer_confidence() -> None:
    response = client.post(
        "/api/v1/eta/calibration",
        json={
            "samples": [
                {
                    "sample_id": "a",
                    "predicted_seconds": 100,
                    "actual_seconds": 110,
                    "interval_lower_seconds": 90,
                    "interval_upper_seconds": 120,
                },
                {
                    "sample_id": "b",
                    "predicted_seconds": 120,
                    "actual_seconds": 100,
                    "interval_lower_seconds": 110,
                    "interval_upper_seconds": 130,
                },
            ],
            "predicted_seconds": 95,
            "sla_seconds": 100,
        },
        headers={"X-Trace-Id": "calibration-trace"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["claim_label"] == "calibration evidence only; not a customer guarantee"
    assert body["status"] == "AVAILABLE"
    assert body["mae_seconds"] == 15
    assert body["interval_coverage"] == 0.5
    assert body["sla_status"] == "AT_RISK"
    assert body["customer_confidence"] == "available"
    assert body["trace_id"] == "calibration-trace"


def test_eta_calibration_gates_confidence_without_samples() -> None:
    response = client.post(
        "/api/v1/eta/calibration",
        json={"predicted_seconds": 80, "sla_seconds": 100},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "UNAVAILABLE"
    assert body["customer_confidence"] == "unavailable"
    assert body["mae_seconds"] is None
