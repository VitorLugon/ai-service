import asyncio
from collections.abc import Sequence

import pytest

from app.core.exceptions import AIProviderInvalidResponseError
from app.knowledge.vector_index import KnowledgeVectorIndex
from app.schemas.knowledge import KnowledgeArticle
from app.schemas.retrieval_evaluation import RetrievalEvaluationCase
from app.schemas.tickets import TicketCategory
from app.services.knowledge_retrieval_evaluator import (
    KnowledgeRetrievalEvaluator,
)


class FakeEmbeddingProvider:
    """Provedor determinístico que não acessa serviços externos."""

    model = "test-embedding-model"

    def __init__(
        self,
        embeddings: list[list[float]],
    ) -> None:
        self.embeddings = embeddings
        self.embed_texts_calls: list[list[str]] = []
        self.embed_text_calls: list[str] = []

    async def embed_text(
        self,
        text: str,
    ) -> list[float]:
        self.embed_text_calls.append(text)

        raise AssertionError("embed_text não deve ser usado pelo avaliador.")

    async def embed_texts(
        self,
        texts: Sequence[str],
    ) -> list[list[float]]:
        self.embed_texts_calls.append(list(texts))

        return self.embeddings


def create_article(
    article_id: str,
) -> KnowledgeArticle:
    """Cria um artigo válido para o índice."""

    return KnowledgeArticle(
        id=article_id,
        title=f"Artigo {article_id}",
        content=(
            "Este conteúdo possui tamanho suficiente para representar "
            "um artigo válido da base de conhecimento."
        ),
        category=TicketCategory.OTHER,
        keywords=["teste"],
    )


def create_case(
    case_id: str,
    query: str,
    relevant_article_ids: list[str],
) -> RetrievalEvaluationCase:
    """Cria um caso de avaliação válido."""

    return RetrievalEvaluationCase(
        id=case_id,
        query=query,
        relevant_article_ids=relevant_article_ids,
    )


def create_index() -> KnowledgeVectorIndex:
    """Cria um índice com ranking controlável por vetores 2D."""

    return KnowledgeVectorIndex(
        articles=[
            create_article("article-a"),
            create_article("article-b"),
            create_article("article-x"),
        ],
        embeddings=[
            [1.0, 0.0],
            [0.0, 1.0],
            [0.8, 0.6],
        ],
    )


def test_retrieval_evaluator_calculates_metrics_and_ranking() -> None:
    provider = FakeEmbeddingProvider(
        embeddings=[
            [0.8, 0.6],
        ],
    )
    evaluator = KnowledgeRetrievalEvaluator(
        embedding_provider=provider,
        index=create_index(),
    )
    case = create_case(
        "case-one",
        "Consulta controlada",
        [
            "article-a",
            "article-b",
        ],
    )

    report = asyncio.run(
        evaluator.evaluate(
            [
                case,
            ],
            k_values=[
                5,
                1,
                3,
            ],
        ),
    )

    assert evaluator.model == "test-embedding-model"
    assert evaluator.indexed_articles == 3
    assert provider.embed_texts_calls == [
        [
            "Consulta controlada",
        ],
    ]
    assert provider.embed_text_calls == []
    assert report.model == "test-embedding-model"
    assert report.indexed_articles == 3
    assert [metric.k for metric in report.metrics] == [
        1,
        3,
        5,
    ]
    assert report.metrics[0].hit_rate == pytest.approx(0.0)
    assert report.metrics[0].mean_recall == pytest.approx(0.0)
    assert report.metrics[1].hit_rate == pytest.approx(1.0)
    assert report.metrics[1].mean_recall == pytest.approx(1.0)
    assert report.metrics[2].hit_rate == pytest.approx(1.0)
    assert report.metrics[2].mean_recall == pytest.approx(1.0)
    assert report.mrr == pytest.approx(0.5)

    result = report.cases[0]

    assert result.case_id == "case-one"
    assert result.query == "Consulta controlada"
    assert result.relevant_article_ids == [
        "article-a",
        "article-b",
    ]
    assert result.retrieved_article_ids == [
        "article-x",
        "article-a",
        "article-b",
    ]
    assert result.first_relevant_rank == 2
    assert result.reciprocal_rank == pytest.approx(0.5)


def test_retrieval_evaluator_preserves_query_order_and_calculates_mrr() -> None:
    provider = FakeEmbeddingProvider(
        embeddings=[
            [0.8, 0.6],
            [1.0, 0.0],
            [-1.0, 0.0],
        ],
    )
    evaluator = KnowledgeRetrievalEvaluator(
        embedding_provider=provider,
        index=create_index(),
    )
    cases = [
        create_case(
            "case-one",
            "Primeira consulta",
            [
                "article-a",
            ],
        ),
        create_case(
            "case-two",
            "Segunda consulta",
            [
                "article-a",
            ],
        ),
        create_case(
            "case-three",
            "Terceira consulta",
            [
                "missing-article",
            ],
        ),
    ]

    report = asyncio.run(
        evaluator.evaluate(
            cases,
        ),
    )

    assert provider.embed_texts_calls == [
        [
            "Primeira consulta",
            "Segunda consulta",
            "Terceira consulta",
        ],
    ]
    assert [result.case_id for result in report.cases] == [
        "case-one",
        "case-two",
        "case-three",
    ]
    assert report.cases[0].first_relevant_rank == 2
    assert report.cases[1].first_relevant_rank == 1
    assert report.cases[2].first_relevant_rank is None
    assert report.cases[2].reciprocal_rank == pytest.approx(0.0)
    assert report.mrr == pytest.approx(0.5)


@pytest.mark.parametrize(
    (
        "cases",
        "k_values",
        "expected_message",
    ),
    [
        (
            [],
            [
                1,
            ],
            "ao menos um caso",
        ),
        (
            [
                create_case(
                    "case-one",
                    "Consulta",
                    [
                        "article-a",
                    ],
                ),
            ],
            [],
            "ao menos um valor de k",
        ),
        (
            [
                create_case(
                    "case-one",
                    "Consulta",
                    [
                        "article-a",
                    ],
                ),
            ],
            [
                0,
            ],
            "maiores que zero",
        ),
        (
            [
                create_case(
                    "case-one",
                    "Consulta",
                    [
                        "article-a",
                    ],
                ),
            ],
            [
                -1,
            ],
            "maiores que zero",
        ),
        (
            [
                create_case(
                    "case-one",
                    "Consulta",
                    [
                        "article-a",
                    ],
                ),
            ],
            [
                1,
                1,
            ],
            "duplicatas",
        ),
    ],
)
def test_retrieval_evaluator_rejects_invalid_inputs(
    cases: list[RetrievalEvaluationCase],
    k_values: list[int],
    expected_message: str,
) -> None:
    evaluator = KnowledgeRetrievalEvaluator(
        embedding_provider=FakeEmbeddingProvider(
            embeddings=[
                [1.0, 0.0],
            ],
        ),
        index=create_index(),
    )

    with pytest.raises(
        ValueError,
        match=expected_message,
    ):
        asyncio.run(
            evaluator.evaluate(
                cases,
                k_values=k_values,
            ),
        )


@pytest.mark.parametrize(
    "embeddings",
    [
        [],
        [
            [1.0, 0.0],
            [0.0, 1.0],
        ],
    ],
)
def test_retrieval_evaluator_rejects_inconsistent_embedding_count(
    embeddings: list[list[float]],
) -> None:
    evaluator = KnowledgeRetrievalEvaluator(
        embedding_provider=FakeEmbeddingProvider(
            embeddings=embeddings,
        ),
        index=create_index(),
    )

    with pytest.raises(AIProviderInvalidResponseError):
        asyncio.run(
            evaluator.evaluate(
                [
                    create_case(
                        "case-one",
                        "Consulta",
                        [
                            "article-a",
                        ],
                    ),
                ],
            ),
        )
