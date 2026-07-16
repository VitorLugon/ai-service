from fastapi import status
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app

client = TestClient(app)


def test_readiness_check_returns_ready() -> None:
    response = client.get("/ready")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "status": "ready",
        "checks": [
            {
                "name": "configuration",
                "status": "ok",
            }
        ],
    }


def test_readiness_check_returns_service_unavailable() -> None:
    def override_get_settings() -> Settings:
        return Settings(app_name="")

    app.dependency_overrides[get_settings] = override_get_settings

    try:
        response = client.get("/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json() == {
        "status": "not_ready",
        "detail": "One or more readiness checks failed.",
        "checks": [
            {
                "name": "configuration",
                "status": "error",
            }
        ],
    }