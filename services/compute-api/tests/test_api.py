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
