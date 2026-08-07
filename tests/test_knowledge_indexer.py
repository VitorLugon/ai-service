import asyncio
from collections.abc import Sequence
from math import inf
from pathlib import Path

import pytest

from app.knowledge.chroma import (
    create_persistent_chroma_client,
    get_or_create_knowledge_collection,
)
from app.schemas.knowledge import KnowledgeArticle
from app.schemas.tickets import TicketCategory
from app.services.knowledge_indexer import (
    ChromaMetadata,
    KnowledgeIndexer,
)


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
    name = "fake-knowledge"

    def __init__(self) -> None:
        self.records: dict[str, tuple[list[float], str, ChromaMetadata]] = {}
        self.upsert_calls = 0
        self.received_ids: list[list[str]] = []

    def count(self) -> int:
        return len(self.records)

    def upsert(
        self,
        *,
        ids: Sequence[str],
        embeddings: Sequence[Sequence[float]],
        documents: Sequence[str],
        metadatas: Sequence[ChromaMetadata],
    ) -> None:
        self.upsert_calls += 1
        self.received_ids.append(
            list(ids),
        )

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


def create_article(
    article_id: str,
) -> KnowledgeArticle:
    return KnowledgeArticle(
        id=article_id,
        title="Artigo para indexação",
        content=("Conteúdo sintético suficientemente longo para validar a indexação."),
        category=TicketCategory.OTHER,
        keywords=[
            "teste",
        ],
    )


def test_knowledge_indexer_upserts_records_idempotently() -> None:
    articles = [
        create_article("first-article"),
        create_article("second-article"),
    ]
    provider = FakeEmbeddingProvider(
        embeddings=[
            [1.0, 0.0],
            [0.0, 1.0],
        ],
    )
    collection = FakeCollection()
    indexer = KnowledgeIndexer(
        embedding_provider=provider,
        collection=collection,
        schema_version=1,
    )

    first_result = asyncio.run(
        indexer.index(
            articles,
        ),
    )
    second_result = asyncio.run(
        indexer.index(
            articles,
        ),
    )

    assert first_result.indexed_articles == 2
    assert first_result.records_before == 0
    assert first_result.records_after == 2
    assert second_result.records_before == 2
    assert second_result.records_after == 2
    assert collection.count() == 2
    assert collection.upsert_calls == 2
    assert collection.received_ids == [
        [
            "first-article",
            "second-article",
        ],
        [
            "first-article",
            "second-article",
        ],
    ]
    assert len(provider.received_batches) == 2
    assert len(provider.received_batches[0]) == 2


def test_knowledge_indexer_persists_records_in_chroma(
    tmp_path: Path,
) -> None:
    articles = [
        create_article("persistent-article"),
    ]
    first_client = create_persistent_chroma_client(
        tmp_path,
    )
    collection = get_or_create_knowledge_collection(
        first_client,
        name="knowledge-indexer-persistence-test",
        schema_version=1,
        embedding_model="text-embedding-test",
    )
    provider = FakeEmbeddingProvider(
        embeddings=[
            [1.0, 0.0],
        ],
    )
    indexer = KnowledgeIndexer(
        embedding_provider=provider,
        collection=collection,
        schema_version=1,
    )

    asyncio.run(
        indexer.index(
            articles,
        ),
    )

    second_client = create_persistent_chroma_client(
        tmp_path,
    )
    persisted_collection = get_or_create_knowledge_collection(
        second_client,
        name="knowledge-indexer-persistence-test",
        schema_version=1,
        embedding_model="text-embedding-test",
    )
    persisted_record = persisted_collection.get(
        ids=[
            "persistent-article",
        ],
    )

    assert persisted_collection.count() == 1
    assert persisted_record["ids"] == [
        "persistent-article",
    ]
    assert persisted_record["documents"] == [
        articles[0].content,
    ]
    assert persisted_record["metadatas"] == [
        {
            "category": "outro",
            "embedding_model": "text-embedding-test",
            "keywords_json": '["teste"]',
            "schema_version": 1,
            "title": "Artigo para indexação",
        },
    ]


@pytest.mark.parametrize(
    ("embeddings", "expected_message"),
    [
        ([[1.0, 0.0]], "quantidade de embeddings"),
        ([[1.0, 0.0], []], "não podem estar vazios"),
        ([[1.0, 0.0], [1.0]], "dimensões inconsistentes"),
        ([[1.0, 0.0], [inf, 0.0]], "valores não finitos"),
    ],
)
def test_knowledge_indexer_rejects_invalid_embeddings(
    embeddings: list[list[float]],
    expected_message: str,
) -> None:
    indexer = KnowledgeIndexer(
        embedding_provider=FakeEmbeddingProvider(
            embeddings=embeddings,
        ),
        collection=FakeCollection(),
        schema_version=1,
    )

    with pytest.raises(
        ValueError,
        match=expected_message,
    ):
        asyncio.run(
            indexer.index(
                [
                    create_article("first-article"),
                    create_article("second-article"),
                ],
            ),
        )


def test_knowledge_indexer_rejects_invalid_schema_version() -> None:
    with pytest.raises(
        ValueError,
        match="maior que zero",
    ):
        KnowledgeIndexer(
            embedding_provider=FakeEmbeddingProvider(
                embeddings=[
                    [1.0, 0.0],
                ],
            ),
            collection=FakeCollection(),
            schema_version=0,
        )
