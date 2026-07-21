from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from openai import AsyncOpenAI

from app.core.config import Settings, get_settings
from app.core.exceptions import AIProviderConfigurationError
from app.services.ticket_classifier import TicketClassifierService


async def get_ticket_classifier(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AsyncIterator[TicketClassifierService]:
    """Cria o classificador e gerencia o cliente da OpenAI."""

    if settings.openai_api_key is None:
        raise AIProviderConfigurationError()

    api_key = settings.openai_api_key.get_secret_value().strip()

    if not api_key:
        raise AIProviderConfigurationError()

    async with AsyncOpenAI(
        api_key=api_key,
        timeout=30.0,
        max_retries=2,
    ) as client:
        yield TicketClassifierService(
            client=client,
            model=settings.openai_model,
        )
