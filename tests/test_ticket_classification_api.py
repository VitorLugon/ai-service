import asyncio
from collections.abc import AsyncIterator
from types import TracebackType
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import status
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.api.dependencies.ticket_classifier import (
    get_ticket_classifier,
)
from app.core.config import Settings
from app.main import app
from app.prompts.ticket_classification import PromptStrategy
from app.schemas.tickets import (
    TicketCategory,
    TicketClassificationResult,
    TicketPriority,
)
from app.services.ticket_classifier import TicketClassifierService


class FakeAsyncOpenAI:
    """Cliente OpenAI falso para validar injecao sem rede."""

    def __init__(self, **_: object) -> None:
        pass

    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        pass


async def resolve_ticket_classifier(
    settings: Settings,
) -> TicketClassifierService:
    dependency = get_ticket_classifier(settings)

    assert isinstance(dependency, AsyncIterator)

    async for classifier in dependency:
        return classifier

    raise AssertionError("Dependency did not yield a classifier.")


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
            "description": ("Não consigo acessar minha conta com a nova senha."),
        },
    )

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json() == {
        "code": "ai_provider_not_configured",
        "detail": "AI provider is not configured.",
        "retryable": False,
    }


def test_ticket_classifier_dependency_uses_configured_prompt_strategy() -> None:
    settings = Settings(
        _env_file=None,
        app_name="AI Service",
        app_version="0.1.0",
        environment="test",
        internal_api_key=SecretStr("test-internal-api-key"),
        openai_api_key=SecretStr("test-openai-api-key"),
        openai_model="test-model",
        openai_prompt_strategy=PromptStrategy.ZERO_SHOT,
    )

    with patch(
        "app.api.dependencies.ticket_classifier.AsyncOpenAI",
        FakeAsyncOpenAI,
    ):
        classifier = asyncio.run(
            resolve_ticket_classifier(settings),
        )

    assert classifier.model == "test-model"
    assert classifier._prompt_strategy is PromptStrategy.ZERO_SHOT
