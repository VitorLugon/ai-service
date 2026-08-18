from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from openai import AsyncOpenAI

from app.api.dependencies.knowledge_search import get_knowledge_search_backend
from app.core.config import Settings, get_settings
from app.core.exceptions import AIProviderConfigurationError
from app.knowledge.search_backend import KnowledgeSearchBackend
from app.rag.context_builder import RagContextBuilder
from app.rag.prompt_builder import RagPromptBuilder
from app.services.embedding_service import EmbeddingService
from app.services.knowledge_search import KnowledgeSearchService
from app.services.rag_answer import RagAnswerComposer
from app.services.rag_generation import RagGenerationService
from app.services.rag_service import RagService


async def get_rag_service(
    backend: Annotated[
        KnowledgeSearchBackend,
        Depends(get_knowledge_search_backend),
    ],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AsyncIterator[RagService]:
    """Cria o serviço RAG completo para uma requisição HTTP."""

    if settings.openai_api_key is None:
        raise AIProviderConfigurationError()

    api_key = settings.openai_api_key.get_secret_value().strip()

    if not api_key:
        raise AIProviderConfigurationError()

    async with AsyncOpenAI(
        api_key=api_key,
        timeout=60.0,
        max_retries=2,
    ) as client:
        search_service = KnowledgeSearchService(
            embedding_provider=EmbeddingService(
                client=client,
                model=settings.openai_embedding_model,
            ),
            index=backend,
        )
        generation_service = RagGenerationService(
            client=client,
            model=settings.openai_rag_model,
            max_output_tokens=settings.rag_max_output_tokens,
        )

        yield RagService(
            search_service=search_service,
            context_builder=RagContextBuilder(
                max_characters=settings.rag_context_max_characters,
            ),
            prompt_builder=RagPromptBuilder(
                question_max_characters=settings.rag_question_max_characters,
            ),
            generation_service=generation_service,
            answer_composer=RagAnswerComposer(),
        )
