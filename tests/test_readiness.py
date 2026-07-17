from fastapi import status
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import Settings, get_settings
from app.main import app


def test_readiness_check_returns_ready(
    client: TestClient,
) -> None:
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


def test_readiness_check_returns_service_unavailable(
    client: TestClient,
) -> None:
    def override_get_invalid_settings() -> Settings:
        return Settings(
            app_name="",
            app_version="0.1.0",
            environment="test",
            internal_api_key=SecretStr("test-internal-api-key"),
        )

    app.dependency_overrides[get_settings] = override_get_invalid_settings

    response = client.get("/ready")

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