from pathlib import Path

import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.core.exceptions import (
    KnowledgeBaseNotIndexedError,
    KnowledgeStoreConfigurationError,
)
from app.knowledge.chroma import (
    create_persistent_chroma_client,
    get_or_create_knowledge_collection,
)
from app.knowledge.chroma_runtime import load_persisted_knowledge_backend
from app.knowledge.indexing import build_knowledge_index_record
from app.prompts.ticket_classification import PromptStrategy
from app.schemas.knowledge import KnowledgeArticle
from app.schemas.tickets import TicketCategory


def create_settings(
    tmp_path: Path,
    *,
    collection_name: str = "knowledge-runtime-test",
    schema_version: int = 1,
    embedding_model: str = "text-embedding-test",
) -> Settings:
    return Settings(
        _env_file=None,
        app_name="AI Service",
        app_version="0.1.0",
        environment="test",
        internal_api_key=SecretStr("test-internal-api-key"),
        openai_api_key=None,
        openai_model="test-model",
        openai_embedding_model=embedding_model,
        openai_prompt_strategy=PromptStrategy.ONE_SHOT,
        chroma_persist_directory=tmp_path,
        chroma_collection_name=collection_name,
        chroma_schema_version=schema_version,
    )


def create_article() -> KnowledgeArticle:
    return KnowledgeArticle(
        id="runtime-article",
        title="Artigo persistido",
        content="Conteúdo sintético suficiente para validar a coleção persistente.",
        category=TicketCategory.OTHER,
        keywords=[
            "teste",
        ],
    )


def create_valid_collection(
    tmp_path: Path,
    *,
    collection_name: str = "knowledge-runtime-test",
    schema_version: int = 1,
    embedding_model: str = "text-embedding-test",
) -> None:
    client = create_persistent_chroma_client(
        tmp_path,
    )
    collection = get_or_create_knowledge_collection(
        client,
        name=collection_name,
        schema_version=schema_version,
        embedding_model=embedding_model,
    )
    record = build_knowledge_index_record(
        create_article(),
        schema_version=schema_version,
        embedding_model=embedding_model,
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


def test_load_persisted_knowledge_backend_accepts_valid_collection(
    tmp_path: Path,
) -> None:
    create_valid_collection(
        tmp_path,
    )

    backend = load_persisted_knowledge_backend(
        create_settings(
            tmp_path,
        ),
    )

    assert backend.size == 1


def test_load_persisted_knowledge_backend_rejects_missing_collection(
    tmp_path: Path,
) -> None:
    create_persistent_chroma_client(
        tmp_path,
    )

    with pytest.raises(
        KnowledgeBaseNotIndexedError,
        match="indexação da base|scripts.index_knowledge_base",
    ):
        load_persisted_knowledge_backend(
            create_settings(
                tmp_path,
            ),
        )


def test_load_persisted_knowledge_backend_rejects_empty_collection(
    tmp_path: Path,
) -> None:
    client = create_persistent_chroma_client(
        tmp_path,
    )
    get_or_create_knowledge_collection(
        client,
        name="knowledge-runtime-test",
        schema_version=1,
        embedding_model="text-embedding-test",
    )

    with pytest.raises(
        KnowledgeBaseNotIndexedError,
        match="vazia",
    ):
        load_persisted_knowledge_backend(
            create_settings(
                tmp_path,
            ),
        )


def test_load_persisted_knowledge_backend_rejects_incompatible_schema(
    tmp_path: Path,
) -> None:
    create_valid_collection(
        tmp_path,
        schema_version=2,
    )

    with pytest.raises(
        KnowledgeStoreConfigurationError,
        match="incompatível",
    ):
        load_persisted_knowledge_backend(
            create_settings(
                tmp_path,
                schema_version=1,
            ),
        )


def test_load_persisted_knowledge_backend_rejects_incompatible_embedding_model(
    tmp_path: Path,
) -> None:
    create_valid_collection(
        tmp_path,
        embedding_model="another-embedding-model",
    )

    with pytest.raises(
        KnowledgeStoreConfigurationError,
        match="incompatível",
    ):
        load_persisted_knowledge_backend(
            create_settings(
                tmp_path,
                embedding_model="text-embedding-test",
            ),
        )


def test_load_persisted_knowledge_backend_rejects_missing_path(
    tmp_path: Path,
) -> None:
    missing_path = tmp_path / "missing" / "chroma"

    with pytest.raises(
        KnowledgeBaseNotIndexedError,
    ):
        load_persisted_knowledge_backend(
            create_settings(
                missing_path,
            ),
        )

    assert missing_path.exists()
