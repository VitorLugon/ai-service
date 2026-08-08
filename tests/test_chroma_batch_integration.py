from pathlib import Path

from app.knowledge.chroma import (
    create_persistent_chroma_client,
    get_or_create_knowledge_collection,
)
from app.knowledge.chroma_backend import ChromaKnowledgeSearchBackend
from app.knowledge.indexing import build_knowledge_index_record
from app.schemas.knowledge import KnowledgeArticle, KnowledgeSearchFilter
from app.schemas.tickets import TicketCategory


def create_article(
    article_id: str,
    *,
    category: TicketCategory = TicketCategory.OTHER,
) -> KnowledgeArticle:
    return KnowledgeArticle(
        id=article_id,
        title=f"Artigo {article_id}",
        content=f"Conteúdo sintético suficiente para validar {article_id}.",
        category=category,
        keywords=[
            "teste",
        ],
    )


def add_article(
    collection: object,
    article: KnowledgeArticle,
    embedding: list[float],
) -> None:
    record = build_knowledge_index_record(
        article,
        schema_version=1,
        embedding_model="text-embedding-test",
    )
    collection.upsert(
        ids=[
            record.id,
        ],
        embeddings=[
            embedding,
        ],
        documents=[
            record.document,
        ],
        metadatas=[
            record.metadata.model_dump(),
        ],
    )


def create_backend(
    tmp_path: Path,
) -> ChromaKnowledgeSearchBackend:
    client = create_persistent_chroma_client(
        tmp_path,
    )
    collection = get_or_create_knowledge_collection(
        client,
        name="knowledge-batch-test",
        schema_version=1,
        embedding_model="text-embedding-test",
    )
    add_article(
        collection,
        create_article(
            "horizontal-access",
            category=TicketCategory.ACCESS_AND_AUTHENTICATION,
        ),
        [
            1.0,
            0.0,
        ],
    )
    add_article(
        collection,
        create_article(
            "mostly-horizontal-billing",
            category=TicketCategory.BILLING,
        ),
        [
            0.9,
            0.1,
        ],
    )
    add_article(
        collection,
        create_article(
            "vertical-technical",
            category=TicketCategory.TECHNICAL_ERROR,
        ),
        [
            0.0,
            1.0,
        ],
    )

    return ChromaKnowledgeSearchBackend(
        collection,
    )


def test_chroma_backend_search_many_preserves_query_order(
    tmp_path: Path,
) -> None:
    backend = create_backend(
        tmp_path,
    )

    results = backend.search_many(
        [
            [
                1.0,
                0.0,
            ],
            [
                0.0,
                1.0,
            ],
        ],
        top_k=2,
    )

    assert len(results) == 2
    assert len(results[0]) <= 2
    assert len(results[1]) <= 2
    assert results[0][0].article.id == "horizontal-access"
    assert results[1][0].article.id == "vertical-technical"


def test_chroma_backend_search_many_combines_batch_and_filter(
    tmp_path: Path,
) -> None:
    backend = create_backend(
        tmp_path,
    )

    results = backend.search_many(
        [
            [
                1.0,
                0.0,
            ],
            [
                0.0,
                1.0,
            ],
        ],
        top_k=3,
        search_filter=KnowledgeSearchFilter(
            category=TicketCategory.ACCESS_AND_AUTHENTICATION,
        ),
    )

    assert [[match.article.id for match in ranking] for ranking in results] == [
        [
            "horizontal-access",
        ],
        [
            "horizontal-access",
        ],
    ]
