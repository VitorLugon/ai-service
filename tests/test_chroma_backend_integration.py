from pathlib import Path

import pytest

from app.knowledge.chroma import (
    create_persistent_chroma_client,
    get_or_create_knowledge_collection,
)
from app.knowledge.chroma_backend import ChromaKnowledgeSearchBackend


def populate_collection(path: Path) -> None:
    client = create_persistent_chroma_client(
        path,
    )
    collection = get_or_create_knowledge_collection(
        client,
        name="knowledge-backend-integration-test",
        schema_version=1,
        embedding_model="text-embedding-test",
    )
    collection.upsert(
        ids=[
            "article-a",
            "article-b",
            "article-c",
        ],
        embeddings=[
            [1.0, 0.0],
            [0.8, 0.2],
            [0.0, 1.0],
        ],
        documents=[
            "Conteúdo sintético suficientemente longo para o artigo A.",
            "Conteúdo sintético suficientemente longo para o artigo B.",
            "Conteúdo sintético suficientemente longo para o artigo C.",
        ],
        metadatas=[
            {
                "title": "Artigo A",
                "category": "outro",
                "keywords_json": '["a"]',
                "schema_version": 1,
                "embedding_model": "text-embedding-test",
            },
            {
                "title": "Artigo B",
                "category": "outro",
                "keywords_json": '["b"]',
                "schema_version": 1,
                "embedding_model": "text-embedding-test",
            },
            {
                "title": "Artigo C",
                "category": "outro",
                "keywords_json": '["c"]',
                "schema_version": 1,
                "embedding_model": "text-embedding-test",
            },
        ],
    )


def test_chroma_backend_searches_persisted_collection(
    tmp_path: Path,
) -> None:
    populate_collection(
        tmp_path,
    )
    client = create_persistent_chroma_client(
        tmp_path,
    )
    collection = get_or_create_knowledge_collection(
        client,
        name="knowledge-backend-integration-test",
        schema_version=1,
        embedding_model="text-embedding-test",
    )
    backend = ChromaKnowledgeSearchBackend(
        collection,
    )

    matches = backend.search(
        [
            1.0,
            0.0,
        ],
        top_k=3,
    )

    assert [match.article.id for match in matches] == [
        "article-a",
        "article-b",
        "article-c",
    ]
    assert matches[0].score == pytest.approx(1.0)
    assert matches[0].article.title == "Artigo A"

    second_client = create_persistent_chroma_client(
        tmp_path,
    )
    persisted_collection = get_or_create_knowledge_collection(
        second_client,
        name="knowledge-backend-integration-test",
        schema_version=1,
        embedding_model="text-embedding-test",
    )
    persisted_matches = ChromaKnowledgeSearchBackend(
        persisted_collection,
    ).search(
        [
            1.0,
            0.0,
        ],
        top_k=1,
    )

    assert persisted_matches[0].article.id == "article-a"
