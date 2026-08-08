from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from openai import AsyncOpenAI

from app.core.app_state import ApplicationResources
from app.core.config import Settings, get_settings
from app.core.exceptions import (
    AIProviderConfigurationError,
    KnowledgeStoreUnavailableError,
)
from app.knowledge.search_backend import KnowledgeSearchBackend
from app.services.embedding_service import EmbeddingService
from app.services.knowledge_batch_search import (
    BatchKnowledgeSearchBackend,
    KnowledgeBatchSearchService,
)
from app.services.knowledge_search import KnowledgeSearchService


def get_knowledge_search_backend(
    request: Request,
) -> KnowledgeSearchBackend:
    """Obtém o backend de busca inicializado no lifespan da aplicação."""

    resources = getattr(
        request.app.state,
        "resources",
        None,
    )

    if not isinstance(
        resources,
        ApplicationResources,
    ):
        raise KnowledgeStoreUnavailableError(
            "Os recursos da aplicação não foram inicializados.",
        )

    return resources.knowledge_search_backend


async def get_knowledge_search_service(
    backend: Annotated[
        KnowledgeSearchBackend,
        Depends(get_knowledge_search_backend),
    ],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AsyncIterator[KnowledgeSearchService]:
    """Cria o serviço de busca semântica e gerencia o cliente da OpenAI."""

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
        embedding_service = EmbeddingService(
            client=client,
            model=settings.openai_embedding_model,
        )

        yield KnowledgeSearchService(
            embedding_provider=embedding_service,
            index=backend,
        )


async def get_knowledge_batch_search_service(
    backend: Annotated[
        KnowledgeSearchBackend,
        Depends(get_knowledge_search_backend),
    ],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AsyncIterator[KnowledgeBatchSearchService]:
    """Cria o serviço de busca semântica em lote."""

    if not isinstance(
        backend,
        BatchKnowledgeSearchBackend,
    ):
        raise KnowledgeStoreUnavailableError(
            "O backend de busca não suporta consultas em lote.",
        )

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
        embedding_service = EmbeddingService(
            client=client,
            model=settings.openai_embedding_model,
        )

        yield KnowledgeBatchSearchService(
            embedding_provider=embedding_service,
            backend=backend,
        )
