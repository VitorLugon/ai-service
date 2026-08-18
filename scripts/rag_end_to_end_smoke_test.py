import asyncio
import sys

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.knowledge.chroma_runtime import load_persisted_knowledge_backend
from app.rag.context_builder import RagContextBuilder
from app.rag.prompt_builder import RagPromptBuilder
from app.services.embedding_service import EmbeddingService
from app.services.knowledge_search import KnowledgeSearchService
from app.services.rag_answer import RagAnswerComposer
from app.services.rag_generation import RagGenerationService
from app.services.rag_service import RagService

SMOKE_QUESTION = (
    "Redefini minha senha, mas ainda não consigo acessar minha conta. O que devo fazer?"
)
SMOKE_TOP_K = 1


async def main() -> None:
    """Executa uma pergunta RAG real usando OpenAI e Chroma persistente."""

    _configure_stdout()
    settings = get_settings()

    if settings.openai_api_key is None:
        raise RuntimeError(
            "OPENAI_API_KEY não está configurada.",
        )

    api_key = settings.openai_api_key.get_secret_value().strip()

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY está vazia.",
        )

    backend = load_persisted_knowledge_backend(
        settings,
    )

    async with AsyncOpenAI(
        api_key=api_key,
        timeout=60.0,
        max_retries=2,
    ) as client:
        service = RagService(
            search_service=KnowledgeSearchService(
                embedding_provider=EmbeddingService(
                    client=client,
                    model=settings.openai_embedding_model,
                ),
                index=backend,
            ),
            context_builder=RagContextBuilder(
                max_characters=settings.rag_context_max_characters,
            ),
            prompt_builder=RagPromptBuilder(
                question_max_characters=settings.rag_question_max_characters,
            ),
            generation_service=RagGenerationService(
                client=client,
                model=settings.openai_rag_model,
                max_output_tokens=settings.rag_max_output_tokens,
            ),
            answer_composer=RagAnswerComposer(),
        )
        answer = await service.answer(
            question=SMOKE_QUESTION,
            top_k=SMOKE_TOP_K,
        )

    print(f"Embedding model: {settings.openai_embedding_model}")
    print(f"Generation model: {settings.openai_rag_model}")
    print(f"Collection: {settings.chroma_collection_name}")
    print(f"Indexed articles: {backend.size}")
    print()
    print(f"Question: {SMOKE_QUESTION}")
    print(f"Answer: {answer.answer}")
    print(f"Sources: {answer.source_count}")

    for source in answer.sources:
        print(
            f"- {source.source_id} | {source.title} | "
            f"{source.category.value} | rank={source.rank}",
        )


def _configure_stdout() -> None:
    if hasattr(
        sys.stdout,
        "reconfigure",
    ):
        sys.stdout.reconfigure(
            encoding="utf-8",
            errors="replace",
        )


if __name__ == "__main__":
    asyncio.run(
        main(),
    )
