import asyncio
from collections.abc import Sequence

import pytest

from app.knowledge.vector_index import KnowledgeVectorIndex
from app.schemas.knowledge import KnowledgeArticle, KnowledgeSearchMatch
from app.schemas.tickets import TicketCategory
from app.services.knowledge_search import (
    KnowledgeSearchService,
    build_knowledge_search_service,
)


def create_article(
    article_id: str,
) -> KnowledgeArticle:
    """Cria um artigo válido para os testes."""

    return KnowledgeArticle(
        id=article_id,
        title="Artigo de conhecimento",
        content=(
            "Este conteúdo possui tamanho suficiente para representar um artigo válido."
        ),
        category=TicketCategory.OTHER,
        keywords=["teste"],
    )


class FakeEmbeddingProvider:
    """Provedor determinístico usado nos testes."""

    model = "test-embedding-model"

    def __init__(
        self,
        *,
        article_embeddings: list[list[float]] | None = None,
        query_embedding: list[float] | None = None,
    ) -> None:
        self.article_embeddings = article_embeddings or [
            [1.0, 0.0],
        ]
        self.query_embedding = query_embedding or [1.0, 0.0]
        self.embedded_text_batches: list[list[str]] = []
        self.embedded_queries: list[str] = []

    async def embed_text(
        self,
        text: str,
    ) -> list[float]:
        self.embedded_queries.append(text)

        return self.query_embedding

    async def embed_texts(
        self,
        texts: Sequence[str],
    ) -> list[list[float]]:
        self.embedded_text_batches.append(list(texts))

        return self.article_embeddings


class FakeKnowledgeSearchBackend:
    """Backend determinístico usado nos testes."""

    def __init__(
        self,
        matches: list[KnowledgeSearchMatch],
    ) -> None:
        self._matches = matches
        self.received_embedding: list[float] | None = None
        self.received_top_k: int | None = None

    @property
    def size(self) -> int:
        """Retorna a quantidade de resultados disponíveis."""

        return len(self._matches)

    def search(
        self,
        query_embedding: Sequence[float],
        *,
        top_k: int = 3,
    ) -> list[KnowledgeSearchMatch]:
        """Retorna resultados determinísticos."""

        self.received_embedding = list(query_embedding)
        self.received_top_k = top_k

        return self._matches[:top_k]


def test_knowledge_search_embeds_normalized_query() -> None:
    article = create_article(
        "matching-article",
    )
    provider = FakeEmbeddingProvider(
        query_embedding=[1.0, 0.0],
    )
    index = KnowledgeVectorIndex(
        articles=[article],
        embeddings=[
            [1.0, 0.0],
        ],
    )

    service = KnowledgeSearchService(
        embedding_provider=provider,
        index=index,
    )

    results = asyncio.run(
        service.search(
            "  recuperar minha senha  ",
            top_k=1,
        ),
    )

    assert provider.embedded_queries == [
        "recuperar minha senha",
    ]
    assert len(results) == 1
    assert results[0].article.id == "matching-article"
    assert results[0].score == pytest.approx(1.0)


def test_knowledge_search_rejects_blank_query() -> None:
    provider = FakeEmbeddingProvider()
    index = KnowledgeVectorIndex(
        articles=[
            create_article(
                "matching-article",
            ),
        ],
        embeddings=[
            [1.0, 0.0],
        ],
    )

    service = KnowledgeSearchService(
        embedding_provider=provider,
        index=index,
    )

    with pytest.raises(
        ValueError,
        match="não pode estar vazia",
    ):
        asyncio.run(
            service.search("   "),
        )

    assert provider.embedded_queries == []


def test_knowledge_search_respects_top_k() -> None:
    provider = FakeEmbeddingProvider(
        query_embedding=[1.0, 0.0],
    )
    index = KnowledgeVectorIndex(
        articles=[
            create_article("first-article"),
            create_article("second-article"),
        ],
        embeddings=[
            [1.0, 0.0],
            [0.8, 0.6],
        ],
    )

    service = KnowledgeSearchService(
        embedding_provider=provider,
        index=index,
    )

    results = asyncio.run(
        service.search(
            "Consulta válida",
            top_k=1,
        ),
    )

    assert len(results) == 1
    assert results[0].article.id == "first-article"


def test_knowledge_search_accepts_backend_protocol() -> None:
    article = create_article(
        "recover-account-access",
    )
    match = KnowledgeSearchMatch(
        article=article,
        score=0.9,
    )
    backend = FakeKnowledgeSearchBackend(
        matches=[
            match,
        ],
    )
    provider = FakeEmbeddingProvider(
        query_embedding=[
            1.0,
            0.0,
        ],
    )
    service = KnowledgeSearchService(
        embedding_provider=provider,
        index=backend,
    )

    results = asyncio.run(
        service.search(
            "  recuperar minha senha  ",
            top_k=1,
        ),
    )

    assert results == [
        match,
    ]
    assert provider.embedded_queries == [
        "recuperar minha senha",
    ]
    assert backend.received_embedding == [
        1.0,
        0.0,
    ]
    assert backend.received_top_k == 1
    assert service.indexed_articles == 1
    assert service.model == "test-embedding-model"


def test_build_knowledge_search_service_builds_index_from_articles() -> None:
    articles = [
        create_article("first-article"),
        create_article("second-article"),
    ]
    provider = FakeEmbeddingProvider(
        article_embeddings=[
            [1.0, 0.0],
            [0.0, 1.0],
        ],
        query_embedding=[1.0, 0.0],
    )

    service = asyncio.run(
        build_knowledge_search_service(
            articles=articles,
            embedding_provider=provider,
        ),
    )

    results = asyncio.run(
        service.search(
            "Artigo de acesso",
            top_k=1,
        ),
    )

    assert service.model == "test-embedding-model"
    assert service.indexed_articles == 2
    assert provider.embedded_text_batches == [
        [
            (
                "Título: Artigo de conhecimento\n"
                "Categoria: outro\n"
                "Palavras-chave: teste\n"
                "Conteúdo: Este conteúdo possui tamanho suficiente "
                "para representar um artigo válido."
            ),
            (
                "Título: Artigo de conhecimento\n"
                "Categoria: outro\n"
                "Palavras-chave: teste\n"
                "Conteúdo: Este conteúdo possui tamanho suficiente "
                "para representar um artigo válido."
            ),
        ],
    ]
    assert provider.embedded_queries == [
        "Artigo de acesso",
    ]
    assert results[0].article.id == "first-article"


def test_build_knowledge_search_service_rejects_empty_articles() -> None:
    provider = FakeEmbeddingProvider()

    with pytest.raises(
        ValueError,
        match="ao menos um artigo",
    ):
        asyncio.run(
            build_knowledge_search_service(
                articles=[],
                embedding_provider=provider,
            ),
        )

    assert provider.embedded_text_batches == []


def test_build_knowledge_search_service_propagates_invalid_embedding_count() -> None:
    provider = FakeEmbeddingProvider(
        article_embeddings=[
            [1.0, 0.0],
        ],
    )

    with pytest.raises(
        ValueError,
        match="quantidade de artigos",
    ):
        asyncio.run(
            build_knowledge_search_service(
                articles=[
                    create_article("first-article"),
                    create_article("second-article"),
                ],
                embedding_provider=provider,
            ),
        )
