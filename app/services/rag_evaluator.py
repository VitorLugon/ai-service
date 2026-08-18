from collections.abc import Sequence
from dataclasses import dataclass
from re import sub
from typing import Protocol
from unicodedata import category, normalize

from app.schemas.rag import RagAnswer
from app.schemas.rag_evaluation import (
    RagEvaluationCase,
    RagEvaluationCaseResult,
    RagEvaluationReport,
    RagExpectedBehavior,
)
from app.schemas.retrieval_evaluation import RetrievalMetricsAtK

DEFAULT_RAG_EVALUATION_K_VALUES = (
    1,
    3,
    5,
)

INSUFFICIENT_EVIDENCE_PATTERNS = (
    "nao encontrei informacao",
    "informacao insuficiente",
    "nao ha informacao suficiente",
    "nao tenho informacao suficiente",
    "nao encontrei evidencia",
    "nao ha evidencia suficiente",
    "sem evidencia suficiente",
    "base de conhecimento nao possui informacao",
)


@dataclass(frozen=True)
class RagEvaluationPipelineOutput:
    """Saída mínima do pipeline RAG necessária para avaliação."""

    retrieved_article_ids: list[str]
    answer: RagAnswer


class RagEvaluationPipeline(Protocol):
    """Pipeline RAG injetável usado pelo evaluator."""

    async def run(
        self,
        question: str,
    ) -> RagEvaluationPipelineOutput:
        """Executa o pipeline para uma pergunta."""


class RagEvaluator:
    """Avalia um pipeline RAG com métricas determinísticas."""

    def __init__(
        self,
        pipeline: RagEvaluationPipeline,
    ) -> None:
        self._pipeline = pipeline

    async def evaluate_case(
        self,
        case: RagEvaluationCase,
    ) -> RagEvaluationCaseResult:
        """Executa e avalia um caso RAG."""

        pipeline_output = await self._pipeline.run(
            case.question,
        )
        answer = pipeline_output.answer
        retrieved_article_ids = pipeline_output.retrieved_article_ids
        returned_source_ids = [source.source_id for source in answer.sources]
        returned_article_ids = [source.article_id for source in answer.sources]
        relevant_article_ids = set(
            case.relevant_article_ids,
        )
        is_answer_case = case.expected_behavior is RagExpectedBehavior.ANSWER
        looks_like_refusal = looks_like_insufficient_evidence_answer(
            answer.answer,
        )
        first_relevant_rank = _find_first_relevant_rank(
            retrieved_article_ids,
            relevant_article_ids,
        )
        reciprocal_rank = (
            0.0 if first_relevant_rank is None else 1.0 / first_relevant_rank
        )

        return RagEvaluationCaseResult(
            case_id=case.id,
            expected_behavior=case.expected_behavior,
            retrieved_article_ids=retrieved_article_ids,
            returned_source_ids=returned_source_ids,
            returned_article_ids=returned_article_ids,
            answer=answer.answer,
            retrieval_hit=is_answer_case and first_relevant_rank is not None,
            source_hit=is_answer_case
            and bool(
                relevant_article_ids.intersection(
                    returned_article_ids,
                ),
            ),
            answer_keyword_coverage=compute_keyword_coverage(
                answer.answer,
                case.expected_answer_keywords,
            ),
            correct_refusal=(
                case.expected_behavior is RagExpectedBehavior.INSUFFICIENT_EVIDENCE
                and looks_like_refusal
            ),
            false_refusal=is_answer_case and looks_like_refusal,
            unsupported_answer=(
                case.expected_behavior is RagExpectedBehavior.INSUFFICIENT_EVIDENCE
                and answer.source_count == 0
                and not looks_like_refusal
            ),
            first_relevant_rank=first_relevant_rank,
            reciprocal_rank=reciprocal_rank,
        )

    async def evaluate(
        self,
        cases: Sequence[RagEvaluationCase],
        *,
        k_values: Sequence[int] = DEFAULT_RAG_EVALUATION_K_VALUES,
    ) -> RagEvaluationReport:
        """Executa todos os casos e agrega métricas por denominador correto."""

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

        results = [
            await self.evaluate_case(
                case,
            )
            for case in cases
        ]
        answer_results = [
            result
            for result in results
            if result.expected_behavior is RagExpectedBehavior.ANSWER
        ]
        insufficient_results = [
            result
            for result in results
            if result.expected_behavior is RagExpectedBehavior.INSUFFICIENT_EVIDENCE
        ]
        coverage_values = [
            result.answer_keyword_coverage
            for result in results
            if result.answer_keyword_coverage is not None
        ]

        return RagEvaluationReport(
            total_cases=len(results),
            answer_cases=len(answer_results),
            insufficient_evidence_cases=len(insufficient_results),
            retrieval_hit_rate=_bool_rate(
                [result.retrieval_hit for result in answer_results],
            ),
            source_hit_rate=_bool_rate(
                [result.source_hit for result in answer_results],
            ),
            mean_answer_keyword_coverage=_mean(
                coverage_values,
            ),
            correct_refusal_rate=_bool_rate(
                [result.correct_refusal for result in insufficient_results],
            ),
            false_refusal_rate=_bool_rate(
                [result.false_refusal for result in answer_results],
            ),
            unsupported_answer_rate=_bool_rate(
                [result.unsupported_answer for result in insufficient_results],
            ),
            retrieval_metrics=_calculate_retrieval_metrics(
                cases=cases,
                results=results,
                k_values=sorted(
                    k_values,
                ),
            ),
            mrr=_mean(
                [result.reciprocal_rank for result in answer_results],
            ),
            case_results=results,
        )


def compute_keyword_coverage(
    answer: str,
    expected_keywords: Sequence[str],
) -> float | None:
    """Calcula cobertura simples de keywords esperadas na resposta."""

    normalized_answer = _normalize_for_matching(
        answer,
    )
    normalized_keywords = []
    seen_keywords: set[str] = set()

    for keyword in expected_keywords:
        normalized_keyword = _normalize_for_matching(
            keyword,
        )

        if not normalized_keyword or normalized_keyword in seen_keywords:
            continue

        seen_keywords.add(
            normalized_keyword,
        )
        normalized_keywords.append(
            normalized_keyword,
        )

    if not normalized_keywords:
        return None

    matched_keywords = sum(
        1 for keyword in normalized_keywords if keyword in normalized_answer
    )

    return matched_keywords / len(normalized_keywords)


def looks_like_insufficient_evidence_answer(
    answer: str,
) -> bool:
    """Detecta recusa por falta de evidência com heurística determinística."""

    normalized_answer = _normalize_for_matching(
        answer,
    )

    return any(
        pattern in normalized_answer for pattern in INSUFFICIENT_EVIDENCE_PATTERNS
    )


def _normalize_for_matching(
    text: str,
) -> str:
    without_accents = "".join(
        character
        for character in normalize(
            "NFKD",
            text,
        )
        if category(character) != "Mn"
    )

    return sub(
        r"\s+",
        " ",
        without_accents.casefold().strip(),
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


def _calculate_retrieval_metrics(
    *,
    cases: Sequence[RagEvaluationCase],
    results: Sequence[RagEvaluationCaseResult],
    k_values: Sequence[int],
) -> list[RetrievalMetricsAtK]:
    answer_pairs = [
        (case, result)
        for case, result in zip(
            cases,
            results,
            strict=True,
        )
        if case.expected_behavior is RagExpectedBehavior.ANSWER
    ]

    if not answer_pairs:
        return []

    metrics: list[RetrievalMetricsAtK] = []

    for k in k_values:
        hit_sum = 0.0
        recall_sum = 0.0

        for case, result in answer_pairs:
            relevant_article_ids = set(
                case.relevant_article_ids,
            )
            retrieved_at_k = set(
                result.retrieved_article_ids[:k],
            )
            relevant_retrieved = len(
                relevant_article_ids.intersection(
                    retrieved_at_k,
                ),
            )

            if relevant_retrieved > 0:
                hit_sum += 1.0

            recall_sum += relevant_retrieved / len(relevant_article_ids)

        total_cases = len(answer_pairs)
        metrics.append(
            RetrievalMetricsAtK(
                k=k,
                hit_rate=hit_sum / total_cases,
                mean_recall=recall_sum / total_cases,
            ),
        )

    return metrics


def _bool_rate(
    values: Sequence[bool],
) -> float | None:
    if not values:
        return None

    return sum(1.0 for value in values if value) / len(values)


def _mean(
    values: Sequence[float],
) -> float | None:
    if not values:
        return None

    return sum(values) / len(values)
