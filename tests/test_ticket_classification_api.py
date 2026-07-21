from unittest.mock import AsyncMock, MagicMock

from fastapi import status
from fastapi.testclient import TestClient

from app.api.dependencies.ticket_classifier import (
    get_ticket_classifier,
)
from app.main import app
from app.schemas.tickets import (
    TicketCategory,
    TicketClassificationResult,
    TicketPriority,
)
from app.services.ticket_classifier import TicketClassifierService


def test_classify_ticket_returns_structured_response(
    client: TestClient,
    api_key: str,
) -> None:
    result = TicketClassificationResult(
        category=TicketCategory.ACCESS_AND_AUTHENTICATION,
        priority=TicketPriority.HIGH,
        summary="Usuário não consegue acessar a conta após trocar a senha.",
        suggested_tags=["login", "senha"],
    )

    classifier = MagicMock(spec=TicketClassifierService)
    classifier.model = "test-model"
    classifier.classify = AsyncMock(return_value=result)

    app.dependency_overrides[get_ticket_classifier] = lambda: classifier

    try:
        response = client.post(
            "/internal/tickets/classify",
            headers={"X-API-Key": api_key},
            json={
                "title": "Não consigo acessar minha conta",
                "description": (
                    "Depois de trocar a senha, o acesso continua bloqueado."
                ),
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_ticket_classifier,
            None,
        )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "category": "acesso_e_autenticacao",
        "priority": "alta",
        "summary": ("Usuário não consegue acessar a conta após trocar a senha."),
        "suggested_tags": ["login", "senha"],
        "model": "test-model",
    }

    classifier.classify.assert_awaited_once()


def test_classify_ticket_requires_internal_api_key(
    client: TestClient,
) -> None:
    response = client.post(
        "/internal/tickets/classify",
        json={
            "title": "Erro ao entrar",
            "description": "Não consigo acessar minha conta com a senha.",
        },
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_classify_ticket_rejects_invalid_input(
    client: TestClient,
    api_key: str,
) -> None:
    classifier = MagicMock(spec=TicketClassifierService)

    app.dependency_overrides[get_ticket_classifier] = lambda: classifier

    try:
        response = client.post(
            "/internal/tickets/classify",
            headers={"X-API-Key": api_key},
            json={
                "title": "X",
                "description": "Erro",
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_ticket_classifier,
            None,
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_classify_ticket_returns_503_without_openai_configuration(
    client: TestClient,
    api_key: str,
) -> None:
    response = client.post(
        "/internal/tickets/classify",
        headers={"X-API-Key": api_key},
        json={
            "title": "Erro ao entrar",
            "description": "Não consigo acessar minha conta com a senha.",
        },
    )

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json() == {
        "code": "ai_provider_not_configured",
        "detail": "AI provider is not configured.",
        "retryable": "False",
    }
