from fastapi.testclient import TestClient

from routemind_compute.api.app import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "UP"}


def test_system_info_declares_non_ownership_of_durable_state() -> None:
    response = client.get("/api/v1/system")

    assert response.status_code == 200
    assert response.json() == {
        "service": "compute-api",
        "runtime": "python",
        "architecture_version": "v1",
        "durable_state_owner": False,
    }
