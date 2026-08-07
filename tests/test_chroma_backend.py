from collections.abc import Mapping, Sequence
from math import inf, nan

import pytest

from app.knowledge.chroma_backend import (
    ChromaKnowledgeInvalidRecordError,
    ChromaKnowledgeSearchBackend,
    cosine_distance_to_similarity,
    knowledge_article_from_chroma_record,
)
from app.services.knowledge_search import KnowledgeSearchService

VALID_DOCUMENT = (
    "Conteúdo sintético suficientemente longo para reconstruir um artigo válido."
)
VALID_METADATA = {
    "title": "Artigo persistido",
    "category": "outro",
    "keywords_json": '["teste"]',
    "schema_version": 1,
    "embedding_model": "text-embedding-test",
}


class FakeChromaCollection:
    def __init__(
        self,
        *,
        count: int,
        query_result: Mapping[str, object] | None = None,
    ) -> None:
        self._count = count
        self._query_result = query_result or {}
        self.query_calls: list[dict[str, object]] = []

    def count(self) -> int:
        return self._count

    def query(
        self,
        *,
        query_embeddings: Sequence[Sequence[float]],
        n_results: int,
        include: Sequence[str],
    ) -> Mapping[str, object]:
        self.query_calls.append(
            {
                "query_embeddings": query_embeddings,
                "n_results": n_results,
                "include": include,
            },
        )

        return self._query_result


class FakeEmbeddingProvider:
    model = "text-embedding-test"

    def __init__(self) -> None:
        self.embedded_queries: list[str] = []

    async def embed_text(
        self,
        text: str,
    ) -> list[float]:
        self.embedded_queries.append(
            text,
        )

        return [
            1.0,
            0.0,
        ]

    async def embed_texts(
        self,
        texts: Sequence[str],
    ) -> list[list[float]]:
        return [
            [
                1.0,
                0.0,
            ]
            for _ in texts
        ]


@pytest.mark.parametrize(
    ("distance", "expected_score"),
    [
        (0.0, 1.0),
        (1.0, 0.0),
        (2.0, -1.0),
    ],
)
def test_cosine_distance_to_similarity(
    distance: float,
    expected_score: float,
) -> None:
    assert cosine_distance_to_similarity(distance) == pytest.approx(expected_score)


@pytest.mark.parametrize(
    "distance",
    [
        nan,
        inf,
        -inf,
    ],
)
def test_cosine_distance_to_similarity_rejects_non_finite_values(
    distance: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="finita",
    ):
        cosine_distance_to_similarity(
            distance,
        )


def test_cosine_distance_to_similarity_accepts_small_tolerance() -> None:
    assert cosine_distance_to_similarity(-1e-10) == pytest.approx(1.0)
    assert cosine_distance_to_similarity(2.0 + 1e-10) == pytest.approx(-1.0)


def test_cosine_distance_to_similarity_rejects_clearly_invalid_values() -> None:
    with pytest.raises(
        ValueError,
        match="fora do intervalo",
    ):
        cosine_distance_to_similarity(
            -0.1,
        )


def test_chroma_backend_size_returns_collection_count() -> None:
    backend = ChromaKnowledgeSearchBackend(
        FakeChromaCollection(
            count=2,
        ),
    )

    assert backend.size == 2


def test_chroma_backend_empty_collection_returns_empty_without_query() -> None:
    collection = FakeChromaCollection(
        count=0,
    )
    backend = ChromaKnowledgeSearchBackend(
        collection,
    )

    assert (
        backend.search(
            [
                1.0,
                0.0,
            ],
        )
        == []
    )
    assert collection.query_calls == []


def test_chroma_backend_search_returns_matches() -> None:
    collection = FakeChromaCollection(
        count=1,
        query_result={
            "ids": [
                [
                    "article-a",
                ],
            ],
            "documents": [
                [
                    VALID_DOCUMENT,
                ],
            ],
            "metadatas": [
                [
                    VALID_METADATA,
                ],
            ],
            "distances": [
                [
                    0.1,
                ],
            ],
        },
    )
    backend = ChromaKnowledgeSearchBackend(
        collection,
    )

    matches = backend.search(
        [
            1.0,
            0.0,
        ],
        top_k=1,
    )

    assert matches[0].article.id == "article-a"
    assert matches[0].article.title == "Artigo persistido"
    assert matches[0].score == pytest.approx(0.9)
    assert collection.query_calls[0]["n_results"] == 1


def test_chroma_backend_limits_top_k_to_collection_size() -> None:
    collection = FakeChromaCollection(
        count=1,
        query_result={
            "ids": [
                [],
            ],
            "documents": [
                [],
            ],
            "metadatas": [
                [],
            ],
            "distances": [
                [],
            ],
        },
    )
    backend = ChromaKnowledgeSearchBackend(
        collection,
    )

    backend.search(
        [
            1.0,
        ],
        top_k=10,
    )

    assert collection.query_calls[0]["n_results"] == 1


@pytest.mark.parametrize(
    "embedding",
    [
        [],
        [
            inf,
        ],
    ],
)
def test_chroma_backend_rejects_invalid_query_embedding(
    embedding: list[float],
) -> None:
    backend = ChromaKnowledgeSearchBackend(
        FakeChromaCollection(
            count=1,
        ),
    )

    with pytest.raises(
        ValueError,
    ):
        backend.search(
            embedding,
        )


@pytest.mark.parametrize(
    "query_result",
    [
        {
            "ids": [
                [
                    "article-a",
                    "article-b",
                ],
            ],
            "documents": [
                [
                    VALID_DOCUMENT,
                ],
            ],
            "metadatas": [
                [
                    VALID_METADATA,
                ],
            ],
            "distances": [
                [
                    0.1,
                ],
            ],
        },
        {
            "ids": [
                [
                    "article-a",
                ],
            ],
            "metadatas": [
                [
                    VALID_METADATA,
                ],
            ],
            "distances": [
                [
                    0.1,
                ],
            ],
        },
        {
            "ids": [
                [
                    "article-a",
                ],
            ],
            "documents": [
                [
                    None,
                ],
            ],
            "metadatas": [
                [
                    VALID_METADATA,
                ],
            ],
            "distances": [
                [
                    0.1,
                ],
            ],
        },
        {
            "ids": [
                [
                    "article-a",
                ],
            ],
            "documents": [
                [
                    VALID_DOCUMENT,
                ],
            ],
            "metadatas": [
                [
                    None,
                ],
            ],
            "distances": [
                [
                    0.1,
                ],
            ],
        },
        {
            "ids": [
                [
                    "article-a",
                ],
            ],
            "documents": [
                [
                    VALID_DOCUMENT,
                ],
            ],
            "metadatas": [
                [
                    VALID_METADATA,
                ],
            ],
        },
        {
            "ids": [
                [
                    "article-a",
                ],
                [
                    "article-b",
                ],
            ],
            "documents": [
                [
                    VALID_DOCUMENT,
                ],
            ],
            "metadatas": [
                [
                    VALID_METADATA,
                ],
            ],
            "distances": [
                [
                    0.1,
                ],
            ],
        },
    ],
)
def test_chroma_backend_rejects_invalid_query_results(
    query_result: Mapping[str, object],
) -> None:
    backend = ChromaKnowledgeSearchBackend(
        FakeChromaCollection(
            count=1,
            query_result=query_result,
        ),
    )

    with pytest.raises(
        ChromaKnowledgeInvalidRecordError,
    ):
        backend.search(
            [
                1.0,
                0.0,
            ],
        )


@pytest.mark.parametrize(
    "metadata",
    [
        {
            **VALID_METADATA,
            "category": "categoria-invalida",
        },
        {
            **VALID_METADATA,
            "keywords_json": "{invalid",
        },
        {
            **VALID_METADATA,
            "keywords_json": '{"not":"list"}',
        },
    ],
)
def test_knowledge_article_from_chroma_record_rejects_invalid_metadata(
    metadata: Mapping[str, object],
) -> None:
    with pytest.raises(
        ChromaKnowledgeInvalidRecordError,
    ):
        knowledge_article_from_chroma_record(
            article_id="article-a",
            document=VALID_DOCUMENT,
            metadata=metadata,
        )


def test_chroma_backend_preserves_chroma_order() -> None:
    backend = ChromaKnowledgeSearchBackend(
        FakeChromaCollection(
            count=2,
            query_result={
                "ids": [
                    [
                        "article-b",
                        "article-a",
                    ],
                ],
                "documents": [
                    [
                        VALID_DOCUMENT,
                        VALID_DOCUMENT,
                    ],
                ],
                "metadatas": [
                    [
                        {
                            **VALID_METADATA,
                            "title": "Segundo artigo",
                        },
                        {
                            **VALID_METADATA,
                            "title": "Primeiro artigo",
                        },
                    ],
                ],
                "distances": [
                    [
                        0.2,
                        0.1,
                    ],
                ],
            },
        ),
    )

    matches = backend.search(
        [
            1.0,
            0.0,
        ],
        top_k=2,
    )

    assert [match.article.id for match in matches] == [
        "article-b",
        "article-a",
    ]


def test_chroma_backend_can_power_knowledge_search_service() -> None:
    import asyncio

    collection = FakeChromaCollection(
        count=1,
        query_result={
            "ids": [
                [
                    "article-a",
                ],
            ],
            "documents": [
                [
                    VALID_DOCUMENT,
                ],
            ],
            "metadatas": [
                [
                    VALID_METADATA,
                ],
            ],
            "distances": [
                [
                    0.0,
                ],
            ],
        },
    )
    provider = FakeEmbeddingProvider()
    service = KnowledgeSearchService(
        embedding_provider=provider,
        index=ChromaKnowledgeSearchBackend(
            collection,
        ),
    )

    matches = asyncio.run(
        service.search(
            "  consulta de teste  ",
            top_k=1,
        ),
    )

    assert provider.embedded_queries == [
        "consulta de teste",
    ]
    assert service.indexed_articles == 1
    assert matches[0].article.id == "article-a"
