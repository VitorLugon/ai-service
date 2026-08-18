from collections.abc import Sequence
from typing import Protocol

from app.schemas.knowledge import (
    KnowledgeSearchFilter,
    KnowledgeSearchMatch,
)
from app.schemas.rag import (
    RagAnswer,
    RagContext,
    RagGenerationResult,
    RagPrompt,
)


class RagSearchService(Protocol):
    """Contrato mínimo da etapa de retrieval."""

    async def search(
        self,
        query: str,
        *,
        top_k: int = 3,
        search_filter: KnowledgeSearchFilter | None = None,
    ) -> list[KnowledgeSearchMatch]:
        """Recupera evidências relevantes para a pergunta."""


class RagContextBuilderService(Protocol):
    """Contrato mínimo da etapa de montagem de contexto."""

    def build(
        self,
        matches: Sequence[KnowledgeSearchMatch],
    ) -> RagContext:
        """Monta o contexto RAG a partir dos matches."""


class RagPromptBuilderService(Protocol):
    """Contrato mínimo da etapa de montagem de prompt."""

    def build(
        self,
        *,
        question: str,
        context: RagContext,
    ) -> RagPrompt:
        """Monta o prompt RAG a partir da pergunta e do contexto."""


class RagGeneratorService(Protocol):
    """Contrato mínimo da etapa generativa."""

    async def generate(
        self,
        prompt: RagPrompt,
    ) -> RagGenerationResult:
        """Gera uma resposta a partir do prompt."""


class RagAnswerComposerService(Protocol):
    """Contrato mínimo da etapa de composição da resposta."""

    def compose(
        self,
        *,
        generation: RagGenerationResult,
        context: RagContext,
    ) -> RagAnswer:
        """Combina geração e sources controladas pela aplicação."""


class RagService:
    """Orquestra o pipeline RAG end-to-end sem depender de FastAPI."""

    def __init__(
        self,
        *,
        search_service: RagSearchService,
        context_builder: RagContextBuilderService,
        prompt_builder: RagPromptBuilderService,
        generation_service: RagGeneratorService,
        answer_composer: RagAnswerComposerService,
    ) -> None:
        self._search_service = search_service
        self._context_builder = context_builder
        self._prompt_builder = prompt_builder
        self._generation_service = generation_service
        self._answer_composer = answer_composer

    async def answer(
        self,
        *,
        question: str,
        top_k: int = 3,
        search_filter: KnowledgeSearchFilter | None = None,
    ) -> RagAnswer:
        """Executa retrieval, context, prompt, generation e answer composition."""

        matches = await self._search_service.search(
            question,
            top_k=top_k,
            search_filter=search_filter,
        )
        context = self._context_builder.build(
            matches,
        )
        prompt = self._prompt_builder.build(
            question=question,
            context=context,
        )
        generation = await self._generation_service.generate(
            prompt,
        )

        return self._answer_composer.compose(
            generation=generation,
            context=context,
        )
