import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.knowledge.vector_index import KnowledgeVectorIndex
from app.schemas.knowledge import KnowledgeArticle
from app.schemas.tickets import TicketCategory
from app.services.knowledge_search import (
    KnowledgeSearchService,
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


def test_knowledge_search_embeds_normalized_query() -> None:
    article = create_article(
        "matching-article",
    )

    index = KnowledgeVectorIndex(
        articles=[article],
        embeddings=[
            [1.0, 0.0],
        ],
    )

    embedding_provider = MagicMock()
    embedding_provider.embed_text = AsyncMock(
        return_value=[1.0, 0.0],
    )

    service = KnowledgeSearchService(
        embedding_provider=embedding_provider,
        index=index,
    )

    results = asyncio.run(
        service.search(
            "  recuperar minha senha  ",
            top_k=1,
        ),
    )

    embedding_provider.embed_text.assert_awaited_once_with(
        "recuperar minha senha",
    )

    assert len(results) == 1
    assert results[0].article.id == "matching-article"
    assert results[0].score == pytest.approx(1.0)


def test_knowledge_search_rejects_blank_query() -> None:
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

    embedding_provider = MagicMock()
    embedding_provider.embed_text = AsyncMock()

    service = KnowledgeSearchService(
        embedding_provider=embedding_provider,
        index=index,
    )

    with pytest.raises(
        ValueError,
        match="não pode estar vazia",
    ):
        asyncio.run(
            service.search("   "),
        )

    embedding_provider.embed_text.assert_not_awaited()


def test_knowledge_search_respects_top_k() -> None:
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

    embedding_provider = MagicMock()
    embedding_provider.embed_text = AsyncMock(
        return_value=[1.0, 0.0],
    )

    service = KnowledgeSearchService(
        embedding_provider=embedding_provider,
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
