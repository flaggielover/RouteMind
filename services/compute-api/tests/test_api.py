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
