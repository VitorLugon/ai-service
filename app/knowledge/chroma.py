from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.collection_configuration import CreateCollectionConfiguration
from chromadb.api.models.Collection import Collection
from chromadb.api.types import Metadata
from chromadb.config import Settings as ChromaSettings

COLLECTION_DESCRIPTION = "Base de conhecimento do HelpDeskLite."
COSINE_COLLECTION_CONFIGURATION = {
    "hnsw": {
        "space": "cosine",
    },
}


def create_persistent_chroma_client(
    path: Path,
) -> ClientAPI:
    """Cria um cliente Chroma persistente em disco."""

    path.mkdir(
        parents=True,
        exist_ok=True,
    )

    return chromadb.PersistentClient(
        path=path,
        settings=ChromaSettings(
            anonymized_telemetry=False,
        ),
    )


def get_or_create_knowledge_collection(
    client: ClientAPI,
    *,
    name: str,
    schema_version: int,
    embedding_model: str,
) -> Collection:
    """Obtém ou cria a coleção persistente da base de conhecimento."""

    normalized_name = _validate_collection_name(
        name,
    )
    normalized_embedding_model = _validate_embedding_model(
        embedding_model,
    )
    _validate_schema_version(
        schema_version,
    )

    expected_metadata = build_knowledge_collection_metadata(
        schema_version=schema_version,
        embedding_model=normalized_embedding_model,
    )

    collection = client.get_or_create_collection(
        name=normalized_name,
        configuration=cast(
            CreateCollectionConfiguration,
            COSINE_COLLECTION_CONFIGURATION,
        ),
        metadata=cast(
            dict[str, Any],
            expected_metadata,
        ),
        embedding_function=None,
    )

    validate_knowledge_collection_metadata(
        collection.metadata,
        expected_metadata=expected_metadata,
    )

    return collection


def get_existing_knowledge_collection(
    client: ClientAPI,
    *,
    name: str,
    schema_version: int,
    embedding_model: str,
) -> Collection:
    """Obtém uma coleção existente da base de conhecimento."""

    normalized_name = _validate_collection_name(
        name,
    )
    normalized_embedding_model = _validate_embedding_model(
        embedding_model,
    )
    _validate_schema_version(
        schema_version,
    )

    expected_metadata = build_knowledge_collection_metadata(
        schema_version=schema_version,
        embedding_model=normalized_embedding_model,
    )

    collection = client.get_collection(
        name=normalized_name,
        embedding_function=None,
    )

    validate_knowledge_collection_metadata(
        collection.metadata,
        expected_metadata=expected_metadata,
    )

    return collection


def _validate_collection_name(
    name: str,
) -> str:
    normalized_name = name.strip()

    if not normalized_name:
        raise ValueError(
            "O nome da coleção Chroma não pode estar vazio.",
        )

    return normalized_name


def _validate_schema_version(
    schema_version: int,
) -> None:
    if schema_version <= 0:
        raise ValueError(
            "A versão do schema da coleção Chroma deve ser maior que zero.",
        )


def _validate_embedding_model(
    embedding_model: str,
) -> str:
    normalized_embedding_model = embedding_model.strip()

    if not normalized_embedding_model:
        raise ValueError(
            "O modelo de embeddings da coleção Chroma não pode estar vazio.",
        )

    return normalized_embedding_model


def build_knowledge_collection_metadata(
    *,
    schema_version: int,
    embedding_model: str,
) -> Metadata:
    """Monta a metadata esperada para a coleção de conhecimento."""

    return {
        "description": COLLECTION_DESCRIPTION,
        "schema_version": schema_version,
        "embedding_model": embedding_model,
    }


def validate_knowledge_collection_metadata(
    metadata: Mapping[str, object] | None,
    *,
    expected_metadata: Mapping[str, object],
) -> None:
    """Valida se a metadata da coleção corresponde à configuração atual."""

    actual_metadata = cast(
        Mapping[str, object],
        metadata or {},
    )

    for field_name, expected_value in expected_metadata.items():
        actual_value = actual_metadata.get(
            field_name,
        )

        if actual_value != expected_value:
            raise ValueError(
                "A coleção existente possui metadata incompatível para "
                f"'{field_name}'.",
            )
