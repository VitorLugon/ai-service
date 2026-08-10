import asyncio
from collections.abc import Sequence
from pathlib import Path

import pytest

from app.knowledge.chroma import (
    create_persistent_chroma_client,
    get_or_create_knowledge_collection,
)
from app.knowledge.chroma_backend import ChromaKnowledgeSearchBackend
from app.knowledge.indexing import build_knowledge_index_record
from app.knowledge.vector_index import KnowledgeVectorIndex
from app.schemas.knowledge import KnowledgeArticle, KnowledgeSearchFilter
from app.schemas.retrieval_evaluation import RetrievalEvaluationCase
from app.schemas.tickets import TicketCategory
from app.services.knowledge_retrieval_evaluator import KnowledgeRetrievalEvaluator

EMBEDDING_MODEL = "text-embedding-test"
SCHEMA_VERSION = 1


class FakeEmbeddingProvider:
    model = EMBEDDING_MODEL

    def __init__(
        self,
        embeddings: list[list[float]],
    ) -> None:
        self.embeddings = embeddings
        self.embed_texts_calls: list[list[str]] = []

    async def embed_text(
        self,
        text: str,
    ) -> list[float]:
        raise AssertionError(
            "A avaliação deve usar embed_texts em lote.",
        )

    async def embed_texts(
        self,
        texts: Sequence[str],
    ) -> list[list[float]]:
        self.embed_texts_calls.append(
            list(texts),
        )

        return self.embeddings


def create_article(
    article_id: str,
    *,
    category: TicketCategory = TicketCategory.OTHER,
) -> KnowledgeArticle:
    return KnowledgeArticle(
        id=article_id,
        title=f"Artigo {article_id}",
        content=f"Conteúdo sintético suficiente para comparar {article_id}.",
        category=category,
        keywords=[
            "teste",
        ],
    )


def create_backends(
    tmp_path: Path,
    *,
    articles: list[KnowledgeArticle] | None = None,
    embeddings: list[list[float]] | None = None,
) -> tuple[KnowledgeVectorIndex, ChromaKnowledgeSearchBackend]:
    resolved_articles = articles or [
        create_article(
            "article-a",
            category=TicketCategory.ACCESS_AND_AUTHENTICATION,
        ),
        create_article(
            "article-b",
            category=TicketCategory.ACCESS_AND_AUTHENTICATION,
        ),
        create_article(
            "article-c",
            category=TicketCategory.TECHNICAL_ERROR,
        ),
        create_article(
            "article-d",
            category=TicketCategory.OTHER,
        ),
    ]
    resolved_embeddings = embeddings or [
        [
            1.0,
            0.0,
        ],
        [
            0.8,
            0.2,
        ],
        [
            0.0,
            1.0,
        ],
        [
            -1.0,
            0.0,
        ],
    ]
    memory_index = KnowledgeVectorIndex(
        articles=resolved_articles,
        embeddings=resolved_embeddings,
    )
    client = create_persistent_chroma_client(
        tmp_path,
    )
    collection = get_or_create_knowledge_collection(
        client,
        name="knowledge-equivalence-test",
        schema_version=SCHEMA_VERSION,
        embedding_model=EMBEDDING_MODEL,
    )
    records = [
        build_knowledge_index_record(
            article,
            schema_version=SCHEMA_VERSION,
            embedding_model=EMBEDDING_MODEL,
        )
        for article in resolved_articles
    ]
    collection.upsert(
        ids=[record.id for record in records],
        embeddings=resolved_embeddings,
        documents=[record.document for record in records],
        metadatas=[record.metadata.model_dump() for record in records],
    )

    return memory_index, ChromaKnowledgeSearchBackend(
        collection,
    )


@pytest.mark.parametrize(
    "top_k",
    [
        1,
        2,
        3,
        10,
    ],
)
def test_memory_and_chroma_return_equivalent_rankings(
    tmp_path: Path,
    top_k: int,
) -> None:
    memory_index, chroma_backend = create_backends(
        tmp_path,
    )

    memory_results = memory_index.search(
        [
            1.0,
            0.0,
        ],
        top_k=top_k,
    )
    chroma_results = chroma_backend.search(
        [
            1.0,
            0.0,
        ],
        top_k=top_k,
    )

    assert [result.article.id for result in chroma_results] == [
        result.article.id for result in memory_results
    ]
    assert [result.article for result in chroma_results] == [
        result.article for result in memory_results
    ]

    for chroma_result, memory_result in zip(
        chroma_results,
        memory_results,
        strict=True,
    ):
        assert chroma_result.score == pytest.approx(
            memory_result.score,
            abs=1e-6,
        )


@pytest.mark.parametrize(
    ("query_embedding", "expected_score"),
    [
        (
            [
                1.0,
                0.0,
            ],
            1.0,
        ),
        (
            [
                0.0,
                1.0,
            ],
            0.0,
        ),
        (
            [
                -1.0,
                0.0,
            ],
            -1.0,
        ),
    ],
)
def test_chroma_scores_match_cosine_reference_cases(
    tmp_path: Path,
    query_embedding: list[float],
    expected_score: float,
) -> None:
    _, chroma_backend = create_backends(
        tmp_path,
        articles=[
            create_article(
                "article-a",
            ),
        ],
        embeddings=[
            [
                1.0,
                0.0,
            ],
        ],
    )

    result = chroma_backend.search(
        query_embedding,
        top_k=1,
    )[0]

    assert result.score == pytest.approx(
        expected_score,
        abs=1e-6,
    )


def test_chroma_tie_contains_same_items_without_forcing_memory_tie_breaker(
    tmp_path: Path,
) -> None:
    articles = [
        create_article(
            "second-article",
        ),
        create_article(
            "first-article",
        ),
    ]
    embeddings = [
        [
            1.0,
            0.0,
        ],
        [
            1.0,
            0.0,
        ],
    ]
    memory_index, chroma_backend = create_backends(
        tmp_path,
        articles=articles,
        embeddings=embeddings,
    )

    memory_results = memory_index.search(
        [
            1.0,
            0.0,
        ],
        top_k=2,
    )
    chroma_results = chroma_backend.search(
        [
            1.0,
            0.0,
        ],
        top_k=2,
    )

    assert [result.article.id for result in memory_results] == [
        "first-article",
        "second-article",
    ]
    assert {result.article.id for result in chroma_results} == {
        "first-article",
        "second-article",
    }
    assert [result.score for result in chroma_results] == [
        pytest.approx(1.0),
        pytest.approx(1.0),
    ]


def test_chroma_category_filter_matches_memory_reference_subset(
    tmp_path: Path,
) -> None:
    memory_index, chroma_backend = create_backends(
        tmp_path,
    )
    eligible_memory_articles = [
        match.article
        for match in memory_index.search(
            [
                1.0,
                0.0,
            ],
            top_k=memory_index.size,
        )
        if match.article.category == TicketCategory.ACCESS_AND_AUTHENTICATION
    ]

    filtered_results = chroma_backend.search_filtered(
        [
            1.0,
            0.0,
        ],
        top_k=3,
        search_filter=KnowledgeSearchFilter(
            category=TicketCategory.ACCESS_AND_AUTHENTICATION,
        ),
    )

    assert [result.article.id for result in filtered_results] == [
        article.id for article in eligible_memory_articles
    ]
    assert all(
        result.article.category == TicketCategory.ACCESS_AND_AUTHENTICATION
        for result in filtered_results
    )


def test_retrieval_metrics_are_equivalent_between_memory_and_chroma(
    tmp_path: Path,
) -> None:
    memory_index, chroma_backend = create_backends(
        tmp_path,
    )
    query_embeddings = [
        [
            1.0,
            0.0,
        ],
        [
            0.0,
            1.0,
        ],
        [
            -1.0,
            0.0,
        ],
    ]
    cases = [
        RetrievalEvaluationCase(
            id="case-a",
            query="Consulta horizontal",
            relevant_article_ids=[
                "article-a",
            ],
        ),
        RetrievalEvaluationCase(
            id="case-c",
            query="Consulta vertical",
            relevant_article_ids=[
                "article-c",
            ],
        ),
        RetrievalEvaluationCase(
            id="case-d",
            query="Consulta oposta",
            relevant_article_ids=[
                "article-d",
            ],
        ),
    ]
    memory_evaluator = KnowledgeRetrievalEvaluator(
        embedding_provider=FakeEmbeddingProvider(
            query_embeddings,
        ),
        index=memory_index,
    )
    chroma_evaluator = KnowledgeRetrievalEvaluator(
        embedding_provider=FakeEmbeddingProvider(
            query_embeddings,
        ),
        index=chroma_backend,
    )

    memory_report = asyncio.run(
        memory_evaluator.evaluate(
            cases,
        ),
    )
    chroma_report = asyncio.run(
        chroma_evaluator.evaluate(
            cases,
        ),
    )

    assert chroma_report.mrr == pytest.approx(
        memory_report.mrr,
    )
    for chroma_metric, memory_metric in zip(
        chroma_report.metrics,
        memory_report.metrics,
        strict=True,
    ):
        assert chroma_metric.k == memory_metric.k
        assert chroma_metric.hit_rate == pytest.approx(
            memory_metric.hit_rate,
        )
        assert chroma_metric.mean_recall == pytest.approx(
            memory_metric.mean_recall,
        )
    assert [case.retrieved_article_ids for case in chroma_report.cases] == [
        case.retrieved_article_ids for case in memory_report.cases
    ]
