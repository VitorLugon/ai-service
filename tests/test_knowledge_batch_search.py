import asyncio
from collections.abc import Sequence

import pytest

from app.schemas.knowledge import (
    KnowledgeArticle,
    KnowledgeSearchFilter,
    KnowledgeSearchMatch,
)
from app.schemas.tickets import TicketCategory
from app.services.knowledge_batch_search import KnowledgeBatchSearchService


def create_match(
    article_id: str,
) -> KnowledgeSearchMatch:
    return KnowledgeSearchMatch(
        article=KnowledgeArticle(
            id=article_id,
            title="Artigo de conhecimento",
            content=(
                "Conteúdo sintético suficiente para representar um artigo válido."
            ),
            category=TicketCategory.OTHER,
            keywords=[
                "teste",
            ],
        ),
        score=1.0,
    )


class FakeEmbeddingProvider:
    model = "test-embedding-model"

    def __init__(
        self,
        embeddings: list[list[float]] | None = None,
    ) -> None:
        self.embeddings = embeddings
        self.embed_text_calls: list[str] = []
        self.embed_texts_calls: list[list[str]] = []

    async def embed_text(
        self,
        text: str,
    ) -> list[float]:
        self.embed_text_calls.append(
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
        self.embed_texts_calls.append(
            list(texts),
        )

        return self.embeddings or [
            [
                1.0,
                0.0,
            ]
            for _ in texts
        ]


class FakeBatchBackend:
    def __init__(
        self,
        rankings: list[list[KnowledgeSearchMatch]] | None = None,
    ) -> None:
        self.rankings = rankings
        self.calls: list[dict[str, object]] = []

    @property
    def size(self) -> int:
        return 12

    def search_many(
        self,
        query_embeddings: Sequence[Sequence[float]],
        *,
        top_k: int = 3,
        search_filter: KnowledgeSearchFilter | None = None,
    ) -> list[list[KnowledgeSearchMatch]]:
        self.calls.append(
            {
                "query_embeddings": [list(embedding) for embedding in query_embeddings],
                "top_k": top_k,
                "search_filter": search_filter,
            },
        )

        return self.rankings or [
            [
                create_match(
                    f"article-{index}",
                ),
            ]
            for index, _ in enumerate(
                query_embeddings,
                start=1,
            )
        ]


def test_knowledge_batch_search_normalizes_queries_and_preserves_order() -> None:
    provider = FakeEmbeddingProvider()
    backend = FakeBatchBackend()
    service = KnowledgeBatchSearchService(
        embedding_provider=provider,
        backend=backend,
    )
    search_filter = KnowledgeSearchFilter(
        category=TicketCategory.BILLING,
    )

    result = asyncio.run(
        service.search_many(
            [
                "  recuperar senha  ",
                "como exportar usuários?   ",
            ],
            top_k=2,
            search_filter=search_filter,
        ),
    )

    assert result.model == "test-embedding-model"
    assert result.indexed_articles == 12
    assert [item.query for item in result.results] == [
        "recuperar senha",
        "como exportar usuários?",
    ]
    assert [item.matches[0].article.id for item in result.results] == [
        "article-1",
        "article-2",
    ]
    assert provider.embed_text_calls == []
    assert provider.embed_texts_calls == [
        [
            "recuperar senha",
            "como exportar usuários?",
        ],
    ]
    assert backend.calls == [
        {
            "query_embeddings": [
                [
                    1.0,
                    0.0,
                ],
                [
                    1.0,
                    0.0,
                ],
            ],
            "top_k": 2,
            "search_filter": search_filter,
        },
    ]


def test_knowledge_batch_search_rejects_empty_batch() -> None:
    service = KnowledgeBatchSearchService(
        embedding_provider=FakeEmbeddingProvider(),
        backend=FakeBatchBackend(),
    )

    with pytest.raises(
        ValueError,
        match="consulta",
    ):
        asyncio.run(
            service.search_many(
                [],
            ),
        )


def test_knowledge_batch_search_rejects_too_many_queries() -> None:
    service = KnowledgeBatchSearchService(
        embedding_provider=FakeEmbeddingProvider(),
        backend=FakeBatchBackend(),
    )

    with pytest.raises(
        ValueError,
        match="máximo",
    ):
        asyncio.run(
            service.search_many(
                [
                    f"consulta {index}"
                    for index in range(
                        21,
                    )
                ],
            ),
        )


def test_knowledge_batch_search_rejects_blank_query_before_provider() -> None:
    provider = FakeEmbeddingProvider()
    service = KnowledgeBatchSearchService(
        embedding_provider=provider,
        backend=FakeBatchBackend(),
    )

    with pytest.raises(
        ValueError,
        match="vazias",
    ):
        asyncio.run(
            service.search_many(
                [
                    "consulta válida",
                    "   ",
                ],
            ),
        )

    assert provider.embed_texts_calls == []


def test_knowledge_batch_search_rejects_embedding_count_mismatch() -> None:
    service = KnowledgeBatchSearchService(
        embedding_provider=FakeEmbeddingProvider(
            embeddings=[
                [
                    1.0,
                    0.0,
                ],
            ],
        ),
        backend=FakeBatchBackend(),
    )

    with pytest.raises(
        ValueError,
        match="embeddings",
    ):
        asyncio.run(
            service.search_many(
                [
                    "consulta um",
                    "consulta dois",
                ],
            ),
        )


def test_knowledge_batch_search_rejects_ranking_count_mismatch() -> None:
    service = KnowledgeBatchSearchService(
        embedding_provider=FakeEmbeddingProvider(),
        backend=FakeBatchBackend(
            rankings=[
                [
                    create_match(
                        "article-only",
                    ),
                ],
            ],
        ),
    )

    with pytest.raises(
        ValueError,
        match="rankings",
    ):
        asyncio.run(
            service.search_many(
                [
                    "consulta um",
                    "consulta dois",
                ],
            ),
        )
