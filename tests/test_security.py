from fastapi import status
from fastapi.testclient import TestClient


def test_internal_ping_rejects_missing_api_key(
    client: TestClient,
) -> None:
    response = client.get("/internal/ping")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {
        "detail": "Invalid or missing API key.",
    }


def test_internal_ping_rejects_invalid_api_key(
    client: TestClient,
) -> None:
    response = client.get(
        "/internal/ping",
        headers={"X-API-Key": "invalid-key"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {
        "detail": "Invalid or missing API key.",
    }


def test_internal_ping_accepts_valid_api_key(
    client: TestClient,
    api_key: str,
) -> None:
    response = client.get(
        "/internal/ping",
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "status": "ok",
        "message": "Internal authentication succeeded.",
    }
