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
    category: TicketCategory,
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


def test_chroma_backend_applies_category_filter_in_chroma(
    tmp_path: Path,
) -> None:
    client = create_persistent_chroma_client(
        tmp_path,
    )
    collection = get_or_create_knowledge_collection(
        client,
        name="knowledge-filter-test",
        schema_version=1,
        embedding_model="text-embedding-test",
    )
    add_article(
        collection,
        create_article(
            "article-access-a",
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
            "article-access-b",
            category=TicketCategory.ACCESS_AND_AUTHENTICATION,
        ),
        [
            0.8,
            0.2,
        ],
    )
    add_article(
        collection,
        create_article(
            "article-billing-a",
            category=TicketCategory.BILLING,
        ),
        [
            0.95,
            0.05,
        ],
    )
    add_article(
        collection,
        create_article(
            "article-technical-a",
            category=TicketCategory.TECHNICAL_ERROR,
        ),
        [
            0.0,
            1.0,
        ],
    )
    backend = ChromaKnowledgeSearchBackend(
        collection,
    )

    unfiltered_matches = backend.search(
        [
            1.0,
            0.0,
        ],
        top_k=3,
    )
    filtered_matches = backend.search_filtered(
        [
            1.0,
            0.0,
        ],
        top_k=3,
        search_filter=KnowledgeSearchFilter(
            category=TicketCategory.ACCESS_AND_AUTHENTICATION,
        ),
    )

    assert "article-billing-a" in [match.article.id for match in unfiltered_matches]
    assert [match.article.category for match in filtered_matches] == [
        TicketCategory.ACCESS_AND_AUTHENTICATION,
        TicketCategory.ACCESS_AND_AUTHENTICATION,
    ]
    assert [match.article.id for match in filtered_matches] == [
        "article-access-a",
        "article-access-b",
    ]
