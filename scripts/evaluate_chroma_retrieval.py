import asyncio
from pathlib import Path

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.evaluation.retrieval_dataset import load_retrieval_evaluation_cases
from app.knowledge.chroma_runtime import load_persisted_knowledge_backend
from app.knowledge.loader import load_knowledge_articles
from app.services.embedding_service import EmbeddingService
from app.services.knowledge_retrieval_evaluator import KnowledgeRetrievalEvaluator
from scripts.evaluate_knowledge_retrieval import DEFAULT_K_VALUES, print_report

KNOWLEDGE_BASE_PATH = Path("knowledge/articles.json")
EVALUATION_DATASET_PATH = Path("evaluation/knowledge_queries.json")


async def main() -> None:
    """Avalia a recuperação semântica usando a coleção Chroma persistente."""

    settings = get_settings()

    if settings.openai_api_key is None:
        raise RuntimeError(
            "OPENAI_API_KEY não foi configurada.",
        )

    api_key = settings.openai_api_key.get_secret_value().strip()

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY está vazia.",
        )

    backend = load_persisted_knowledge_backend(
        settings,
    )
    articles = load_knowledge_articles(
        KNOWLEDGE_BASE_PATH,
    )
    cases = load_retrieval_evaluation_cases(
        EVALUATION_DATASET_PATH,
        known_article_ids={article.id for article in articles},
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
        evaluator = KnowledgeRetrievalEvaluator(
            embedding_provider=embedding_service,
            index=backend,
        )
        report = await evaluator.evaluate(
            cases,
            k_values=DEFAULT_K_VALUES,
        )

    print_report(
        report,
    )


if __name__ == "__main__":
    asyncio.run(
        main(),
    )
