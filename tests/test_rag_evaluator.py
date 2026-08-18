import asyncio
from copy import deepcopy

from app.schemas.rag import RagAnswer, RagAnswerSource
from app.schemas.rag_evaluation import RagEvaluationCase, RagExpectedBehavior
from app.schemas.tickets import TicketCategory
from app.services.rag_evaluator import (
    RagEvaluationPipelineOutput,
    RagEvaluator,
)


class FakeRagPipeline:
    def __init__(
        self,
        outputs: dict[str, RagEvaluationPipelineOutput],
    ) -> None:
        self._outputs = outputs
        self.questions: list[str] = []

    async def run(
        self,
        question: str,
    ) -> RagEvaluationPipelineOutput:
        self.questions.append(
            question,
        )

        return self._outputs[question]


def source(
    article_id: str,
    *,
    rank: int = 1,
    chunk_id: str | None = None,
) -> RagAnswerSource:
    return RagAnswerSource(
        source_id=chunk_id or article_id,
        article_id=article_id,
        chunk_id=chunk_id,
        title=f"Artigo {article_id}",
        category=TicketCategory.ACCESS_AND_AUTHENTICATION,
        rank=rank,
    )


def answer(
    text: str,
    *,
    sources: list[RagAnswerSource] | None = None,
) -> RagAnswer:
    answer_sources = sources or []

    return RagAnswer(
        answer=text,
        sources=answer_sources,
        source_count=len(answer_sources),
    )


def pipeline_output(
    *,
    retrieved_article_ids: list[str],
    rag_answer: RagAnswer,
) -> RagEvaluationPipelineOutput:
    return RagEvaluationPipelineOutput(
        retrieved_article_ids=retrieved_article_ids,
        answer=rag_answer,
    )


def case(
    case_id: str,
    *,
    question: str,
    relevant_article_ids: list[str],
    keywords: list[str],
    behavior: RagExpectedBehavior = RagExpectedBehavior.ANSWER,
) -> RagEvaluationCase:
    return RagEvaluationCase(
        id=case_id,
        question=question,
        relevant_article_ids=relevant_article_ids,
        expected_answer_keywords=keywords,
        expected_behavior=behavior,
    )


def no_evidence_case(
    case_id: str,
    *,
    question: str,
) -> RagEvaluationCase:
    return RagEvaluationCase(
        id=case_id,
        question=question,
        relevant_article_ids=[],
        expected_answer_keywords=[],
        expected_behavior=RagExpectedBehavior.INSUFFICIENT_EVIDENCE,
    )


def evaluate_single(
    evaluation_case: RagEvaluationCase,
    output: RagEvaluationPipelineOutput,
):
    return asyncio.run(
        RagEvaluator(
            FakeRagPipeline(
                {
                    evaluation_case.question: output,
                },
            ),
        ).evaluate_case(
            evaluation_case,
        ),
    )


def test_rag_evaluator_evaluates_correct_positive_case() -> None:
    evaluation_case = case(
        "rag-access",
        question="Como recupero acesso?",
        relevant_article_ids=[
            "recover-account-access",
        ],
        keywords=[
            "senha",
            "login",
        ],
    )

    result = evaluate_single(
        evaluation_case,
        pipeline_output(
            retrieved_article_ids=[
                "recover-account-access",
            ],
            rag_answer=answer(
                "Use a opção de senha na tela de login.",
                sources=[
                    source(
                        "recover-account-access",
                    ),
                ],
            ),
        ),
    )

    assert result.retrieval_hit
    assert result.source_hit
    assert result.answer_keyword_coverage == 1.0
    assert not result.false_refusal
    assert result.first_relevant_rank == 1
    assert result.reciprocal_rank == 1.0


def test_rag_evaluator_separates_retrieval_miss() -> None:
    evaluation_case = case(
        "rag-retrieval-miss",
        question="Como recupero acesso?",
        relevant_article_ids=[
            "article-a",
        ],
        keywords=[
            "senha",
        ],
    )

    result = evaluate_single(
        evaluation_case,
        pipeline_output(
            retrieved_article_ids=[
                "article-b",
            ],
            rag_answer=answer(
                "Não encontrei informação suficiente.",
                sources=[
                    source(
                        "article-b",
                    ),
                ],
            ),
        ),
    )

    assert not result.retrieval_hit
    assert not result.source_hit
    assert result.false_refusal


def test_rag_evaluator_separates_source_loss_after_retrieval_hit() -> None:
    evaluation_case = case(
        "rag-source-loss",
        question="Como recupero acesso?",
        relevant_article_ids=[
            "article-a",
        ],
        keywords=[
            "senha",
        ],
    )

    result = evaluate_single(
        evaluation_case,
        pipeline_output(
            retrieved_article_ids=[
                "article-a",
                "article-b",
            ],
            rag_answer=answer(
                "Use senha temporária.",
                sources=[
                    source(
                        "article-b",
                    ),
                ],
            ),
        ),
    )

    assert result.retrieval_hit
    assert not result.source_hit
    assert result.answer_keyword_coverage == 1.0


def test_rag_evaluator_detects_partial_keyword_coverage() -> None:
    evaluation_case = case(
        "rag-partial-coverage",
        question="Como exporto usuários?",
        relevant_article_ids=[
            "export-users-to-csv",
        ],
        keywords=[
            "csv",
            "administração",
        ],
    )

    result = evaluate_single(
        evaluation_case,
        pipeline_output(
            retrieved_article_ids=[
                "export-users-to-csv",
            ],
            rag_answer=answer(
                "Exporte os usuários para CSV.",
                sources=[
                    source(
                        "export-users-to-csv",
                    ),
                ],
            ),
        ),
    )

    assert result.answer_keyword_coverage == 0.5


def test_rag_evaluator_detects_correct_refusal() -> None:
    evaluation_case = no_evidence_case(
        "rag-correct-refusal",
        question="Qual é a política de férias?",
    )

    result = evaluate_single(
        evaluation_case,
        pipeline_output(
            retrieved_article_ids=[],
            rag_answer=answer(
                "Não encontrei informação suficiente na base.",
            ),
        ),
    )

    assert result.correct_refusal
    assert not result.unsupported_answer
    assert result.answer_keyword_coverage is None


def test_rag_evaluator_detects_false_refusal() -> None:
    evaluation_case = case(
        "rag-false-refusal",
        question="Como exporto usuários?",
        relevant_article_ids=[
            "export-users-to-csv",
        ],
        keywords=[
            "csv",
        ],
    )

    result = evaluate_single(
        evaluation_case,
        pipeline_output(
            retrieved_article_ids=[
                "export-users-to-csv",
            ],
            rag_answer=answer(
                "Não tenho informação suficiente para responder.",
                sources=[
                    source(
                        "export-users-to-csv",
                    ),
                ],
            ),
        ),
    )

    assert result.retrieval_hit
    assert result.source_hit
    assert result.false_refusal


def test_rag_evaluator_detects_unsupported_answer() -> None:
    evaluation_case = no_evidence_case(
        "rag-unsupported",
        question="Vai chover amanhã?",
    )

    result = evaluate_single(
        evaluation_case,
        pipeline_output(
            retrieved_article_ids=[],
            rag_answer=answer(
                "A previsão indica chuva no fim da tarde.",
            ),
        ),
    )

    assert result.unsupported_answer
    assert not result.correct_refusal


def test_rag_evaluator_ignores_source_hallucination_in_answer_text() -> None:
    evaluation_case = case(
        "rag-source-hallucination",
        question="Como recupero acesso?",
        relevant_article_ids=[
            "article-a",
        ],
        keywords=[
            "senha",
        ],
    )

    result = evaluate_single(
        evaluation_case,
        pipeline_output(
            retrieved_article_ids=[
                "article-a",
            ],
            rag_answer=answer(
                "Segundo SOURCE 999, use a senha.",
                sources=[
                    source(
                        "article-a",
                    ),
                ],
            ),
        ),
    )

    assert result.source_hit
    assert result.returned_source_ids == [
        "article-a",
    ]


def test_rag_evaluator_handles_multiple_sources() -> None:
    evaluation_case = case(
        "rag-multiple-sources",
        question="Acesso e MFA",
        relevant_article_ids=[
            "article-a",
            "article-b",
        ],
        keywords=[
            "senha",
            "mfa",
        ],
    )

    result = evaluate_single(
        evaluation_case,
        pipeline_output(
            retrieved_article_ids=[
                "article-a",
                "article-b",
            ],
            rag_answer=answer(
                "Use senha e configure MFA.",
                sources=[
                    source(
                        "article-a",
                        rank=1,
                    ),
                    source(
                        "article-b",
                        rank=2,
                        chunk_id="article-b#chunk-000",
                    ),
                ],
            ),
        ),
    )

    assert result.retrieval_hit
    assert result.source_hit
    assert result.returned_article_ids == [
        "article-a",
        "article-b",
    ]
    assert result.returned_source_ids == [
        "article-a",
        "article-b#chunk-000",
    ]


def test_rag_evaluator_aggregates_report_and_preserves_case_order() -> None:
    cases = [
        case(
            "rag-first",
            question="Primeira pergunta?",
            relevant_article_ids=[
                "article-a",
            ],
            keywords=[
                "senha",
            ],
        ),
        no_evidence_case(
            "rag-second",
            question="Segunda pergunta?",
        ),
    ]
    pipeline = FakeRagPipeline(
        {
            "Primeira pergunta?": pipeline_output(
                retrieved_article_ids=[
                    "article-a",
                ],
                rag_answer=answer(
                    "Use senha.",
                    sources=[
                        source(
                            "article-a",
                        ),
                    ],
                ),
            ),
            "Segunda pergunta?": pipeline_output(
                retrieved_article_ids=[],
                rag_answer=answer(
                    "Não encontrei informação suficiente.",
                ),
            ),
        },
    )

    report = asyncio.run(
        RagEvaluator(
            pipeline,
        ).evaluate(
            cases,
            k_values=[
                1,
                3,
            ],
        ),
    )

    assert [result.case_id for result in report.case_results] == [
        "rag-first",
        "rag-second",
    ]
    assert pipeline.questions == [
        "Primeira pergunta?",
        "Segunda pergunta?",
    ]
    assert report.retrieval_hit_rate == 1.0
    assert report.source_hit_rate == 1.0
    assert report.correct_refusal_rate == 1.0
    assert [metric.k for metric in report.retrieval_metrics] == [
        1,
        3,
    ]


def test_rag_evaluator_is_deterministic_and_does_not_mutate_inputs() -> None:
    evaluation_case = case(
        "rag-deterministic",
        question="Como recupero acesso?",
        relevant_article_ids=[
            "article-a",
        ],
        keywords=[
            "senha",
        ],
    )
    output = pipeline_output(
        retrieved_article_ids=[
            "article-a",
        ],
        rag_answer=answer(
            "Use senha.",
            sources=[
                source(
                    "article-a",
                ),
            ],
        ),
    )
    case_before = deepcopy(
        evaluation_case.model_dump(),
    )
    output_before = deepcopy(
        output,
    )

    first_result = evaluate_single(
        evaluation_case,
        output,
    )
    second_result = evaluate_single(
        evaluation_case,
        output,
    )

    assert first_result == second_result
    assert evaluation_case.model_dump() == case_before
    assert output == output_before
