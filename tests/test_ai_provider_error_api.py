from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.api.dependencies.ticket_classifier import (
    get_ticket_classifier,
)
from app.core.exceptions import (
    AIProviderConfigurationError,
    AIProviderConnectionError,
    AIProviderError,
    AIProviderInvalidResponseError,
    AIProviderRateLimitError,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
)
from app.main import app
from app.services.ticket_classifier import TicketClassifierService


@pytest.mark.parametrize(
    (
        "provider_error",
        "expected_status",
        "expected_code",
        "expected_retryable",
    ),
    [
        (
            AIProviderTimeoutError(),
            status.HTTP_504_GATEWAY_TIMEOUT,
            "ai_provider_timeout",
            True,
        ),
        (
            AIProviderConnectionError(),
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "ai_provider_unreachable",
            True,
        ),
        (
            AIProviderRateLimitError(),
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "ai_provider_rate_limited",
            True,
        ),
        (
            AIProviderUnavailableError(),
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "ai_provider_unavailable",
            True,
        ),
        (
            AIProviderConfigurationError(),
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "ai_provider_not_configured",
            False,
        ),
        (
            AIProviderInvalidResponseError(),
            status.HTTP_502_BAD_GATEWAY,
            "ai_provider_invalid_response",
            False,
        ),
    ],
)
def test_classification_maps_provider_errors(
    client: TestClient,
    api_key: str,
    provider_error: AIProviderError,
    expected_status: int,
    expected_code: str,
    expected_retryable: bool,
) -> None:
    classifier = MagicMock(spec=TicketClassifierService)
    classifier.classify = AsyncMock(
        side_effect=provider_error,
    )

    app.dependency_overrides[get_ticket_classifier] = lambda: classifier

    try:
        response = client.post(
            "/internal/tickets/classify",
            headers={"X-API-Key": api_key},
            json={
                "title": "Não consigo acessar",
                "description": ("Não consigo acessar minha conta com a nova senha."),
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_ticket_classifier,
            None,
        )

    assert response.status_code == expected_status
    assert response.json()["code"] == expected_code
    assert response.json()["retryable"] is expected_retryable


def test_rate_limit_response_includes_retry_after(
    client: TestClient,
    api_key: str,
) -> None:
    classifier = MagicMock(spec=TicketClassifierService)
    classifier.classify = AsyncMock(
        side_effect=AIProviderRateLimitError(),
    )

    app.dependency_overrides[get_ticket_classifier] = lambda: classifier

    try:
        response = client.post(
            "/internal/tickets/classify",
            headers={"X-API-Key": api_key},
            json={
                "title": "Não consigo acessar",
                "description": ("Não consigo acessar minha conta com a nova senha."),
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_ticket_classifier,
            None,
        )

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.headers["Retry-After"] == "30"
