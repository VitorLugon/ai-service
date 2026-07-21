import asyncio
from unittest.mock import AsyncMock, MagicMock

import httpx
import openai
import pytest

from app.core.exceptions import (
    AIProviderConfigurationError,
    AIProviderConnectionError,
    AIProviderError,
    AIProviderRateLimitError,
    AIProviderRequestError,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
)
from app.schemas.tickets import TicketClassificationInput
from app.services.ticket_classifier import TicketClassifierService

REQUEST = httpx.Request(
    "POST",
    "https://api.openai.com/v1/responses",
)


def create_ticket() -> TicketClassificationInput:
    """Cria um chamado válido."""

    return TicketClassificationInput(
        title="Erro ao entrar",
        description="Não consigo acessar minha conta com a nova senha.",
    )


@pytest.mark.parametrize(
    ("sdk_error", "application_error"),
    [
        (
            openai.APITimeoutError(request=REQUEST),
            AIProviderTimeoutError,
        ),
        (
            openai.APIConnectionError(request=REQUEST),
            AIProviderConnectionError,
        ),
        (
            openai.RateLimitError(
                "Rate limit",
                response=httpx.Response(
                    429,
                    request=REQUEST,
                ),
                body=None,
            ),
            AIProviderRateLimitError,
        ),
        (
            openai.AuthenticationError(
                "Invalid API key",
                response=httpx.Response(
                    401,
                    request=REQUEST,
                ),
                body=None,
            ),
            AIProviderConfigurationError,
        ),
        (
            openai.InternalServerError(
                "Provider error",
                response=httpx.Response(
                    500,
                    request=REQUEST,
                ),
                body=None,
            ),
            AIProviderUnavailableError,
        ),
        (
            openai.BadRequestError(
                "Bad request",
                response=httpx.Response(
                    400,
                    request=REQUEST,
                ),
                body=None,
            ),
            AIProviderRequestError,
        ),
    ],
)
def test_classifier_translates_openai_errors(
    sdk_error: Exception,
    application_error: type[AIProviderError],
) -> None:
    client = MagicMock()
    client.responses.parse = AsyncMock(
        side_effect=sdk_error,
    )

    classifier = TicketClassifierService(
        client=client,
        model="test-model",
    )

    with pytest.raises(application_error):
        asyncio.run(
            classifier.classify(create_ticket()),
        )
