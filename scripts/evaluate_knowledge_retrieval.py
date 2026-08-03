import asyncio
from pathlib import Path

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.evaluation.retrieval_dataset import (
    load_retrieval_evaluation_cases,
)
from app.knowledge.loader import load_knowledge_articles
from app.knowledge.text import build_knowledge_article_embedding_text
from app.knowledge.vector_index import KnowledgeVectorIndex
from app.schemas.retrieval_evaluation import RetrievalEvaluationReport
from app.services.embedding_service import EmbeddingService
from app.services.knowledge_retrieval_evaluator import (
    KnowledgeRetrievalEvaluator,
)

KNOWLEDGE_BASE_PATH = Path("knowledge/articles.json")
EVALUATION_DATASET_PATH = Path("evaluation/knowledge_queries.json")
DEFAULT_K_VALUES = (
    1,
    3,
    5,
)


def print_report(
    report: RetrievalEvaluationReport,
) -> None:
    """Exibe métricas agregadas e casos que merecem revisão."""

    print(f"Modelo: {report.model}")
    print(f"Artigos indexados: {report.indexed_articles}")
    print(f"Consultas avaliadas: {report.total_cases}")
    print("")

    for metric in report.metrics:
        print(f"Hit Rate@{metric.k}: {metric.hit_rate:.4f}")
        print(f"Recall@{metric.k}: {metric.mean_recall:.4f}")
        print("")

    print(f"MRR: {report.mrr:.4f}")

    cases_without_first_rank_hit = [
        result for result in report.cases if result.first_relevant_rank != 1
    ]

    if cases_without_first_rank_hit:
        print("")
        print("Casos cujo primeiro relevante não ficou na primeira posição:")

        for result in cases_without_first_rank_hit:
            first_rank = (
                "não encontrado"
                if result.first_relevant_rank is None
                else str(result.first_relevant_rank)
            )
            first_retrieved_ids = ", ".join(
                result.retrieved_article_ids[:5],
            )

            print(
                f"- {result.case_id}: rank={first_rank}; "
                f"primeiros={first_retrieved_ids}"
            )

    cases_with_incomplete_top_3 = [
        result
        for result in report.cases
        if not set(result.relevant_article_ids).issubset(
            set(result.retrieved_article_ids[:3]),
        )
    ]

    if cases_with_incomplete_top_3:
        print("")
        print("Casos sem todos os relevantes no top 3:")

        for result in cases_with_incomplete_top_3:
            first_retrieved_ids = ", ".join(
                result.retrieved_article_ids[:3],
            )

            print(f"- {result.case_id}: top3={first_retrieved_ids}")


async def main() -> None:
    """Executa a avaliação real da recuperação semântica."""

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

    articles = load_knowledge_articles(
        KNOWLEDGE_BASE_PATH,
    )
    known_article_ids = {article.id for article in articles}
    cases = load_retrieval_evaluation_cases(
        EVALUATION_DATASET_PATH,
        known_article_ids=known_article_ids,
    )
    article_texts = [
        build_knowledge_article_embedding_text(
            article,
        )
        for article in articles
    ]

    async with AsyncOpenAI(
        api_key=api_key,
        timeout=30.0,
        max_retries=2,
    ) as client:
        embedding_service = EmbeddingService(
            client=client,
            model=settings.openai_embedding_model,
        )
        article_embeddings = await embedding_service.embed_texts(
            article_texts,
        )
        index = KnowledgeVectorIndex(
            articles=articles,
            embeddings=article_embeddings,
        )
        evaluator = KnowledgeRetrievalEvaluator(
            embedding_provider=embedding_service,
            index=index,
        )
        report = await evaluator.evaluate(
            cases,
            k_values=DEFAULT_K_VALUES,
        )

    print_report(
        report,
    )


if __name__ == "__main__":
    asyncio.run(main())
