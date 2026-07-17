from fastapi.testclient import TestClient


def test_health_check_returns_service_status(
    client: TestClient,
) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "AI Service",
        "version": "0.1.0",
    }