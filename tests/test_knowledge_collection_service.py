import asyncio
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from app.knowledge.chroma import (
    create_persistent_chroma_client,
    get_or_create_knowledge_collection,
)
from app.schemas.knowledge import KnowledgeArticle
from app.schemas.tickets import TicketCategory
from app.services.knowledge_collection_service import (
    KnowledgeArticleNotFoundError,
    KnowledgeCollectionService,
)
from app.services.knowledge_indexer import ChromaMetadata


class FakeEmbeddingProvider:
    model = "text-embedding-test"

    def __init__(
        self,
        embeddings: list[list[float]],
    ) -> None:
        self._embeddings = embeddings
        self.received_batches: list[list[str]] = []

    async def embed_texts(
        self,
        texts: Sequence[str],
    ) -> list[list[float]]:
        self.received_batches.append(
            list(texts),
        )

        return self._embeddings


class FakeCollection:
    name = "fake-maintenance"

    def __init__(self) -> None:
        self.records: dict[str, tuple[list[float], str, ChromaMetadata]] = {}
        self.deleted_ids: list[list[str]] = []
        self.upsert_calls = 0

    def count(self) -> int:
        return len(self.records)

    def get(
        self,
        *,
        ids: Sequence[str],
    ) -> Mapping[str, object]:
        existing_ids = [article_id for article_id in ids if article_id in self.records]

        return {
            "ids": existing_ids,
        }

    def upsert(
        self,
        *,
        ids: Sequence[str],
        embeddings: Sequence[Sequence[float]],
        documents: Sequence[str],
        metadatas: Sequence[ChromaMetadata],
    ) -> None:
        self.upsert_calls += 1

        for article_id, embedding, document, metadata in zip(
            ids,
            embeddings,
            documents,
            metadatas,
            strict=True,
        ):
            self.records[article_id] = (
                list(embedding),
                document,
                metadata,
            )

    def delete(
        self,
        *,
        ids: Sequence[str],
    ) -> object:
        self.deleted_ids.append(
            list(ids),
        )

        for article_id in ids:
            self.records.pop(
                article_id,
                None,
            )

        return None


def create_article(
    article_id: str,
    *,
    content: str = "Conteúdo sintético suficientemente longo para manutenção.",
) -> KnowledgeArticle:
    return KnowledgeArticle(
        id=article_id,
        title="Artigo de manutenção",
        content=content,
        category=TicketCategory.OTHER,
        keywords=[
            "teste",
        ],
    )


def test_update_article_updates_existing_record() -> None:
    collection = FakeCollection()
    article = create_article(
        "existing-article",
    )
    collection.records[article.id] = (
        [
            0.0,
            1.0,
        ],
        "Documento antigo suficientemente longo.",
        {
            "title": "Antigo",
            "category": "outro",
            "keywords_json": '["antigo"]',
            "schema_version": 1,
            "embedding_model": "text-embedding-test",
        },
    )
    provider = FakeEmbeddingProvider(
        embeddings=[
            [
                1.0,
                0.0,
            ],
        ],
    )
    service = KnowledgeCollectionService(
        embedding_provider=provider,
        collection=collection,
        schema_version=1,
    )

    result = asyncio.run(
        service.update_article(
            article,
        ),
    )

    assert result.records_before == 1
    assert result.records_after == 1
    assert collection.upsert_calls == 1
    assert provider.received_batches
    assert collection.records[article.id][0] == [
        1.0,
        0.0,
    ]
    assert collection.records[article.id][1] == article.content
    assert collection.records[article.id][2]["title"] == "Artigo de manutenção"


def test_update_article_rejects_missing_id_without_embedding() -> None:
    provider = FakeEmbeddingProvider(
        embeddings=[
            [
                1.0,
            ],
        ],
    )
    collection = FakeCollection()
    service = KnowledgeCollectionService(
        embedding_provider=provider,
        collection=collection,
        schema_version=1,
    )

    with pytest.raises(
        KnowledgeArticleNotFoundError,
    ):
        asyncio.run(
            service.update_article(
                create_article("missing-article"),
            ),
        )

    assert provider.received_batches == []
    assert collection.upsert_calls == 0


def test_delete_article_removes_existing_record() -> None:
    collection = FakeCollection()
    article = create_article(
        "existing-article",
    )
    collection.records[article.id] = (
        [
            1.0,
        ],
        article.content,
        {
            "title": article.title,
            "category": "outro",
            "keywords_json": '["teste"]',
            "schema_version": 1,
            "embedding_model": "text-embedding-test",
        },
    )
    service = KnowledgeCollectionService(
        embedding_provider=FakeEmbeddingProvider(
            embeddings=[
                [
                    1.0,
                ],
            ],
        ),
        collection=collection,
        schema_version=1,
    )

    result = service.delete_article(
        article.id,
    )

    assert result.records_before == 1
    assert result.records_after == 0
    assert result.deleted_article_id == article.id
    assert collection.deleted_ids == [
        [
            article.id,
        ],
    ]


def test_delete_article_rejects_missing_id_without_delete() -> None:
    collection = FakeCollection()
    service = KnowledgeCollectionService(
        embedding_provider=FakeEmbeddingProvider(
            embeddings=[
                [
                    1.0,
                ],
            ],
        ),
        collection=collection,
        schema_version=1,
    )

    with pytest.raises(
        KnowledgeArticleNotFoundError,
    ):
        service.delete_article(
            "missing-article",
        )

    assert collection.deleted_ids == []


def test_delete_article_rejects_empty_id() -> None:
    service = KnowledgeCollectionService(
        embedding_provider=FakeEmbeddingProvider(
            embeddings=[
                [
                    1.0,
                ],
            ],
        ),
        collection=FakeCollection(),
        schema_version=1,
    )

    with pytest.raises(
        ValueError,
        match="não pode estar vazio",
    ):
        service.delete_article(
            "   ",
        )


def test_knowledge_collection_service_updates_and_deletes_real_chroma_record(
    tmp_path: Path,
) -> None:
    client = create_persistent_chroma_client(
        tmp_path,
    )
    collection = get_or_create_knowledge_collection(
        client,
        name="knowledge-maintenance-integration-test",
        schema_version=1,
        embedding_model="text-embedding-test",
    )
    article = create_article(
        "temporary-article",
    )
    collection.upsert(
        ids=[
            article.id,
        ],
        embeddings=[
            [
                0.0,
                1.0,
            ],
        ],
        documents=[
            article.content,
        ],
        metadatas=[
            {
                "title": article.title,
                "category": "outro",
                "keywords_json": '["teste"]',
                "schema_version": 1,
                "embedding_model": "text-embedding-test",
            },
        ],
    )
    updated_article = create_article(
        article.id,
        content="Conteúdo atualizado suficientemente longo para manutenção.",
    )
    service = KnowledgeCollectionService(
        embedding_provider=FakeEmbeddingProvider(
            embeddings=[
                [
                    1.0,
                    0.0,
                ],
            ],
        ),
        collection=collection,
        schema_version=1,
    )

    update_result = asyncio.run(
        service.update_article(
            updated_article,
        ),
    )
    updated_record = collection.get(
        ids=[
            article.id,
        ],
    )
    delete_result = service.delete_article(
        article.id,
    )

    assert update_result.records_before == 1
    assert update_result.records_after == 1
    assert updated_record["documents"] == [
        updated_article.content,
    ]
    assert updated_record["metadatas"][0]["title"] == "Artigo de manutenção"
    assert delete_result.records_before == 1
    assert delete_result.records_after == 0
    assert (
        collection.get(
            ids=[
                article.id,
            ],
        )["ids"]
        == []
    )
