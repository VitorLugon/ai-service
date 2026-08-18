import asyncio

import pytest
from pydantic import ValidationError

from app.schemas.rag import RagAnswer
from app.schemas.rag_evaluation import (
    RagEvaluationCase,
    RagEvaluationReport,
    RagExpectedBehavior,
)
from app.services.rag_evaluator import (
    RagEvaluationPipelineOutput,
    RagEvaluator,
    compute_keyword_coverage,
    looks_like_insufficient_evidence_answer,
)


class EmptyPipeline:
    async def run(
        self,
        question: str,
    ) -> RagEvaluationPipelineOutput:
        return RagEvaluationPipelineOutput(
            retrieved_article_ids=[],
            answer=RagAnswer(
                answer="Não encontrei informação suficiente na base.",
                sources=[],
                source_count=0,
            ),
        )


def answer_case(
    case_id: str = "rag-answer",
    *,
    relevant_article_ids: list[str] | None = None,
    keywords: list[str] | None = None,
) -> RagEvaluationCase:
    return RagEvaluationCase(
        id=case_id,
        question=f"Pergunta para {case_id}?",
        relevant_article_ids=relevant_article_ids
        or [
            "article-a",
        ],
        expected_answer_keywords=keywords
        or [
            "senha",
        ],
        expected_behavior=RagExpectedBehavior.ANSWER,
    )


def no_evidence_case(
    case_id: str = "rag-no-evidence",
) -> RagEvaluationCase:
    return RagEvaluationCase(
        id=case_id,
        question=f"Pergunta fora da base {case_id}?",
        relevant_article_ids=[],
        expected_answer_keywords=[],
        expected_behavior=RagExpectedBehavior.INSUFFICIENT_EVIDENCE,
    )


@pytest.mark.parametrize(
    ("answer", "keywords", "expected"),
    [
        ("Resposta sem termos esperados.", ["senha", "login"], 0.0),
        ("Use a senha temporária.", ["senha", "login"], 0.5),
        ("Use a senha no login.", ["senha", "login"], 1.0),
        ("USE A SENHA NO LOGIN.", ["senha", "login"], 1.0),
        ("  Use   a   senha   no   login. ", [" senha ", " login "], 1.0),
        ("Use senha.", ["senha", "senha", "SENHA"], 1.0),
    ],
)
def test_compute_keyword_coverage(
    answer: str,
    keywords: list[str],
    expected: float,
) -> None:
    assert (
        compute_keyword_coverage(
            answer,
            keywords,
        )
        == expected
    )


def test_compute_keyword_coverage_returns_none_without_keywords() -> None:
    assert (
        compute_keyword_coverage(
            "Qualquer resposta.",
            [],
        )
        is None
    )


def test_compute_keyword_coverage_ignores_blank_duplicate_keywords() -> None:
    assert (
        compute_keyword_coverage(
            "Use senha e login.",
            [
                "senha",
                " ",
                "login",
                "LOGIN",
            ],
        )
        == 1.0
    )


@pytest.mark.parametrize(
    "answer",
    [
        "Não encontrei informação suficiente na base.",
        "A INFORMAÇÃO INSUFICIENTE impede resposta.",
        "Não há informação suficiente para responder.",
        "Não tenho informação suficiente no contexto.",
        "Sem evidência suficiente na base.",
    ],
)
def test_looks_like_insufficient_evidence_answer_detects_known_phrases(
    answer: str,
) -> None:
    assert looks_like_insufficient_evidence_answer(
        answer,
    )


def test_looks_like_insufficient_evidence_answer_rejects_substantive_answer() -> None:
    assert not looks_like_insufficient_evidence_answer(
        "Acesse a área de administração e exporte os usuários em CSV.",
    )


def test_rag_evaluator_rejects_empty_cases() -> None:
    evaluator = RagEvaluator(
        EmptyPipeline(),
    )

    with pytest.raises(
        ValueError,
        match="ao menos um caso",
    ):
        asyncio.run(
            evaluator.evaluate(
                [],
            ),
        )


def test_rag_evaluator_rejects_invalid_k_values() -> None:
    evaluator = RagEvaluator(
        EmptyPipeline(),
    )

    with pytest.raises(
        ValueError,
        match="maiores que zero",
    ):
        asyncio.run(
            evaluator.evaluate(
                [
                    no_evidence_case(),
                ],
                k_values=[
                    0,
                ],
            ),
        )


def test_rag_evaluator_rejects_duplicate_k_values() -> None:
    evaluator = RagEvaluator(
        EmptyPipeline(),
    )

    with pytest.raises(
        ValueError,
        match="duplicatas",
    ):
        asyncio.run(
            evaluator.evaluate(
                [
                    no_evidence_case(),
                ],
                k_values=[
                    1,
                    1,
                ],
            ),
        )


def test_rag_evaluator_uses_correct_aggregation_denominators() -> None:
    class MixedPipeline:
        async def run(
            self,
            question: str,
        ) -> RagEvaluationPipelineOutput:
            if "answer-good" in question:
                return RagEvaluationPipelineOutput(
                    retrieved_article_ids=[
                        "article-a",
                    ],
                    answer=RagAnswer(
                        answer="Use senha.",
                        sources=[],
                        source_count=0,
                    ),
                )

            if "answer-refusal" in question:
                return RagEvaluationPipelineOutput(
                    retrieved_article_ids=[
                        "article-b",
                    ],
                    answer=RagAnswer(
                        answer="Não encontrei informação suficiente.",
                        sources=[],
                        source_count=0,
                    ),
                )

            return RagEvaluationPipelineOutput(
                retrieved_article_ids=[],
                answer=RagAnswer(
                    answer="Não encontrei informação suficiente.",
                    sources=[],
                    source_count=0,
                ),
            )

    report = asyncio.run(
        RagEvaluator(
            MixedPipeline(),
        ).evaluate(
            [
                answer_case(
                    "rag-answer-good",
                    relevant_article_ids=[
                        "article-a",
                    ],
                    keywords=[
                        "senha",
                    ],
                ),
                answer_case(
                    "rag-answer-refusal",
                    relevant_article_ids=[
                        "article-b",
                    ],
                    keywords=[
                        "senha",
                    ],
                ),
                no_evidence_case(),
            ],
            k_values=[
                1,
            ],
        ),
    )

    assert report.total_cases == 3
    assert report.answer_cases == 2
    assert report.insufficient_evidence_cases == 1
    assert report.retrieval_hit_rate == 1.0
    assert report.source_hit_rate == 0.0
    assert report.mean_answer_keyword_coverage == 0.5
    assert report.correct_refusal_rate == 1.0
    assert report.false_refusal_rate == 0.5
    assert report.unsupported_answer_rate == 0.0
    assert report.retrieval_metrics[0].hit_rate == 1.0
    assert report.retrieval_metrics[0].mean_recall == 1.0
    assert report.mrr == 1.0


def test_rag_evaluator_returns_none_for_not_applicable_metrics() -> None:
    report = asyncio.run(
        RagEvaluator(
            EmptyPipeline(),
        ).evaluate(
            [
                no_evidence_case(),
            ],
        ),
    )

    assert report.retrieval_hit_rate is None
    assert report.source_hit_rate is None
    assert report.mean_answer_keyword_coverage is None
    assert report.false_refusal_rate is None
    assert report.retrieval_metrics == []
    assert report.mrr is None
    assert report.correct_refusal_rate == 1.0
    assert report.unsupported_answer_rate == 0.0


def test_rag_evaluation_report_rejects_inconsistent_counts() -> None:
    with pytest.raises(
        ValidationError,
    ):
        RagEvaluationReport(
            total_cases=2,
            answer_cases=1,
            insufficient_evidence_cases=0,
            retrieval_hit_rate=None,
            source_hit_rate=None,
            mean_answer_keyword_coverage=None,
            correct_refusal_rate=None,
            false_refusal_rate=None,
            unsupported_answer_rate=None,
            retrieval_metrics=[],
            mrr=None,
            case_results=[],
        )
