from collections.abc import Sequence
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import Settings
from app.core.exceptions import KnowledgeBaseNotIndexedError
from app.knowledge.chroma import (
    create_persistent_chroma_client,
    get_or_create_knowledge_collection,
)
from app.knowledge.indexing import build_knowledge_index_record
from app.main import create_application
from app.prompts.ticket_classification import PromptStrategy
from app.schemas.knowledge import KnowledgeArticle, KnowledgeSearchMatch
from app.schemas.tickets import TicketCategory


class FakeKnowledgeSearchBackend:
    def __init__(
        self,
        *,
        size: int,
    ) -> None:
        self._size = size

    @property
    def size(self) -> int:
        return self._size

    def search(
        self,
        query_embedding: Sequence[float],
        *,
        top_k: int = 3,
    ) -> list[KnowledgeSearchMatch]:
        return []


def create_settings(
    tmp_path: Path,
    *,
    collection_name: str = "knowledge-lifespan-test",
) -> Settings:
    return Settings(
        _env_file=None,
        app_name="AI Service",
        app_version="0.1.0",
        environment="test",
        internal_api_key=SecretStr("test-internal-api-key"),
        openai_api_key=None,
        openai_model="test-model",
        openai_embedding_model="text-embedding-test",
        openai_prompt_strategy=PromptStrategy.ONE_SHOT,
        chroma_persist_directory=tmp_path,
        chroma_collection_name=collection_name,
        chroma_schema_version=1,
    )


def create_article() -> KnowledgeArticle:
    return KnowledgeArticle(
        id="lifespan-article",
        title="Artigo de lifecycle",
        content="Conteúdo sintético suficiente para validar o ciclo de vida.",
        category=TicketCategory.OTHER,
        keywords=[
            "lifecycle",
        ],
    )


def create_indexed_collection(
    tmp_path: Path,
    *,
    collection_name: str = "knowledge-lifespan-test",
) -> None:
    client = create_persistent_chroma_client(
        tmp_path,
    )
    collection = get_or_create_knowledge_collection(
        client,
        name=collection_name,
        schema_version=1,
        embedding_model="text-embedding-test",
    )
    record = build_knowledge_index_record(
        create_article(),
        schema_version=1,
        embedding_model="text-embedding-test",
    )
    collection.upsert(
        ids=[
            record.id,
        ],
        embeddings=[
            [
                1.0,
                0.0,
            ],
        ],
        documents=[
            record.document,
        ],
        metadatas=[
            record.metadata.model_dump(),
        ],
    )


def test_lifespan_loads_backend_into_app_state(
    tmp_path: Path,
) -> None:
    create_indexed_collection(
        tmp_path,
    )
    app = create_application(
        settings=create_settings(
            tmp_path,
        ),
    )

    with TestClient(app):
        assert app.state.resources.knowledge_search_backend.size == 1


def test_lifespan_rejects_missing_collection_without_creating_it(
    tmp_path: Path,
) -> None:
    app = create_application(
        settings=create_settings(
            tmp_path,
        ),
    )

    with pytest.raises(
        KnowledgeBaseNotIndexedError,
    ):
        with TestClient(app):
            pass

    client = create_persistent_chroma_client(
        tmp_path,
    )

    assert client.list_collections() == []


def test_lifespan_accepts_injected_backend_without_chroma(
    tmp_path: Path,
) -> None:
    backend = FakeKnowledgeSearchBackend(
        size=9,
    )
    app = create_application(
        settings=create_settings(
            tmp_path,
        ),
        knowledge_search_backend=backend,
    )

    with TestClient(app):
        assert app.state.resources.knowledge_search_backend is backend
        assert app.state.resources.knowledge_search_backend.size == 9


def test_lifespan_resources_do_not_leak_between_app_instances(
    tmp_path: Path,
) -> None:
    first_backend = FakeKnowledgeSearchBackend(
        size=1,
    )
    second_backend = FakeKnowledgeSearchBackend(
        size=2,
    )
    first_app = create_application(
        settings=create_settings(
            tmp_path / "first",
            collection_name="knowledge-first-test",
        ),
        knowledge_search_backend=first_backend,
    )
    second_app = create_application(
        settings=create_settings(
            tmp_path / "second",
            collection_name="knowledge-second-test",
        ),
        knowledge_search_backend=second_backend,
    )

    with TestClient(first_app):
        assert first_app.state.resources.knowledge_search_backend is first_backend

    with TestClient(second_app):
        assert second_app.state.resources.knowledge_search_backend is second_backend
