from collections.abc import Sequence

from app.core.exceptions import AIProviderInvalidResponseError
from app.knowledge.vector_index import KnowledgeVectorIndex
from app.schemas.retrieval_evaluation import (
    RetrievalCaseResult,
    RetrievalEvaluationCase,
    RetrievalEvaluationReport,
    RetrievalMetricsAtK,
)
from app.services.knowledge_search import EmbeddingProvider


class KnowledgeRetrievalEvaluator:
    """Avalia a qualidade da recuperação semântica."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        index: KnowledgeVectorIndex,
    ) -> None:
        self._embedding_provider = embedding_provider
        self._index = index

    @property
    def model(self) -> str:
        """Retorna o modelo de embeddings utilizado."""

        return self._embedding_provider.model

    @property
    def indexed_articles(self) -> int:
        """Retorna a quantidade de artigos indexados."""

        return self._index.size

    async def evaluate(
        self,
        cases: Sequence[RetrievalEvaluationCase],
        *,
        k_values: Sequence[int] = (1, 3, 5),
    ) -> RetrievalEvaluationReport:
        """Executa a avaliação e calcula métricas de recuperação."""

        if not cases:
            raise ValueError(
                "É necessário informar ao menos um caso.",
            )

        if not k_values:
            raise ValueError(
                "É necessário informar ao menos um valor de k.",
            )

        if any(k < 1 for k in k_values):
            raise ValueError(
                "Os valores de k devem ser maiores que zero.",
            )

        if len(k_values) != len(set(k_values)):
            raise ValueError(
                "Os valores de k não podem conter duplicatas.",
            )

        sorted_k_values = sorted(k_values)

        query_embeddings = await self._embedding_provider.embed_texts(
            [case.query for case in cases],
        )

        if len(query_embeddings) != len(cases):
            raise AIProviderInvalidResponseError()

        results: list[RetrievalCaseResult] = []

        for case, query_embedding in zip(
            cases,
            query_embeddings,
            strict=True,
        ):
            matches = self._index.search(
                query_embedding,
                top_k=self._index.size,
            )
            retrieved_article_ids = [match.article.id for match in matches]
            relevant_article_ids = set(case.relevant_article_ids)
            first_relevant_rank = _find_first_relevant_rank(
                retrieved_article_ids,
                relevant_article_ids,
            )
            reciprocal_rank = (
                0.0 if first_relevant_rank is None else 1.0 / first_relevant_rank
            )

            results.append(
                RetrievalCaseResult(
                    case_id=case.id,
                    query=case.query,
                    relevant_article_ids=case.relevant_article_ids,
                    retrieved_article_ids=retrieved_article_ids,
                    first_relevant_rank=first_relevant_rank,
                    reciprocal_rank=reciprocal_rank,
                ),
            )

        metrics = [
            _calculate_metrics_at_k(
                k=k,
                cases=cases,
                results=results,
            )
            for k in sorted_k_values
        ]
        total_cases = len(results)
        mrr = sum(result.reciprocal_rank for result in results) / total_cases

        return RetrievalEvaluationReport(
            model=self.model,
            total_cases=total_cases,
            indexed_articles=self.indexed_articles,
            metrics=metrics,
            mrr=mrr,
            cases=results,
        )


def _find_first_relevant_rank(
    retrieved_article_ids: Sequence[str],
    relevant_article_ids: set[str],
) -> int | None:
    for rank, article_id in enumerate(
        retrieved_article_ids,
        start=1,
    ):
        if article_id in relevant_article_ids:
            return rank

    return None


def _calculate_metrics_at_k(
    *,
    k: int,
    cases: Sequence[RetrievalEvaluationCase],
    results: Sequence[RetrievalCaseResult],
) -> RetrievalMetricsAtK:
    hit_sum = 0.0
    recall_sum = 0.0

    for case, result in zip(
        cases,
        results,
        strict=True,
    ):
        relevant_article_ids = set(case.relevant_article_ids)
        retrieved_at_k = set(result.retrieved_article_ids[:k])
        relevant_retrieved = len(
            relevant_article_ids.intersection(
                retrieved_at_k,
            ),
        )

        if relevant_retrieved > 0:
            hit_sum += 1.0

        recall_sum += relevant_retrieved / len(relevant_article_ids)

    total_cases = len(cases)

    return RetrievalMetricsAtK(
        k=k,
        hit_rate=hit_sum / total_cases,
        mean_recall=recall_sum / total_cases,
    )
