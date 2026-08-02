from collections.abc import AsyncIterator
from pathlib import Path
from typing import Annotated

from fastapi import Depends
from openai import AsyncOpenAI

from app.core.config import Settings, get_settings
from app.core.exceptions import AIProviderConfigurationError
from app.knowledge.loader import load_knowledge_articles
from app.services.embedding_service import EmbeddingService
from app.services.knowledge_search import (
    KnowledgeSearchService,
    build_knowledge_search_service,
)

KNOWLEDGE_BASE_PATH = Path("knowledge/articles.json")


async def get_knowledge_search_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AsyncIterator[KnowledgeSearchService]:
    """Cria o serviço de busca semântica e gerencia o cliente da OpenAI."""

    if settings.openai_api_key is None:
        raise AIProviderConfigurationError()

    api_key = settings.openai_api_key.get_secret_value().strip()

    if not api_key:
        raise AIProviderConfigurationError()

    articles = load_knowledge_articles(
        KNOWLEDGE_BASE_PATH,
    )

    async with AsyncOpenAI(
        api_key=api_key,
        timeout=30.0,
        max_retries=2,
    ) as client:
        embedding_service = EmbeddingService(
            client=client,
            model=settings.openai_embedding_model,
        )

        yield await build_knowledge_search_service(
            articles=articles,
            embedding_provider=embedding_service,
        )
