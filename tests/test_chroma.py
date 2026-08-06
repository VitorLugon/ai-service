from collections.abc import Sequence
from pathlib import Path

import pytest
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection

from app.knowledge.chroma import (
    COLLECTION_DESCRIPTION,
    create_persistent_chroma_client,
    get_or_create_knowledge_collection,
)

EMBEDDING_MODEL = "text-embedding-test"
SCHEMA_VERSION = 1


def collection_names(
    client: ClientAPI,
) -> list[str]:
    names: list[str] = []

    for collection in client.list_collections():
        names.append(
            collection.name,
        )

    return names


def create_collection(
    path: Path,
    *,
    name: str = "knowledge-test",
    schema_version: int = SCHEMA_VERSION,
    embedding_model: str = EMBEDDING_MODEL,
) -> tuple[ClientAPI, Collection]:
    client = create_persistent_chroma_client(
        path,
    )
    collection = get_or_create_knowledge_collection(
        client,
        name=name,
        schema_version=schema_version,
        embedding_model=embedding_model,
    )

    return client, collection


def assert_expected_metadata(
    collection: Collection,
    *,
    schema_version: int = SCHEMA_VERSION,
    embedding_model: str = EMBEDDING_MODEL,
) -> None:
    assert collection.metadata is not None
    assert collection.metadata["description"] == COLLECTION_DESCRIPTION
    assert collection.metadata["schema_version"] == schema_version
    assert collection.metadata["embedding_model"] == embedding_model


def test_create_persistent_chroma_client_creates_directory(
    tmp_path: Path,
) -> None:
    persist_path = tmp_path / "nested" / "chroma"

    create_persistent_chroma_client(
        persist_path,
    )

    assert persist_path.exists()
    assert persist_path.is_dir()


def test_get_or_create_knowledge_collection_creates_empty_collection(
    tmp_path: Path,
) -> None:
    client, collection = create_collection(
        tmp_path,
        name="knowledge-empty-test",
    )

    assert collection.name == "knowledge-empty-test"
    assert collection.count() == 0
    assert collection_names(client) == [
        "knowledge-empty-test",
    ]


def test_get_or_create_knowledge_collection_is_idempotent(
    tmp_path: Path,
) -> None:
    client, first_collection = create_collection(
        tmp_path,
        name="knowledge-idempotent-test",
    )
    second_collection = get_or_create_knowledge_collection(
        client,
        name="knowledge-idempotent-test",
        schema_version=SCHEMA_VERSION,
        embedding_model=EMBEDDING_MODEL,
    )

    assert first_collection.name == second_collection.name
    assert collection_names(client) == [
        "knowledge-idempotent-test",
    ]
    assert_expected_metadata(second_collection)


def test_get_or_create_knowledge_collection_sets_expected_metadata(
    tmp_path: Path,
) -> None:
    _, collection = create_collection(
        tmp_path,
        name="knowledge-metadata-test",
    )

    assert_expected_metadata(collection)


@pytest.mark.parametrize(
    ("schema_version", "embedding_model", "expected_field"),
    [
        (2, EMBEDDING_MODEL, "schema_version"),
        (SCHEMA_VERSION, "another-model", "embedding_model"),
    ],
)
def test_get_or_create_knowledge_collection_rejects_incompatible_metadata(
    tmp_path: Path,
    schema_version: int,
    embedding_model: str,
    expected_field: str,
) -> None:
    client, _ = create_collection(
        tmp_path,
        name="knowledge-incompatible-test",
    )

    with pytest.raises(
        ValueError,
        match=f"metadata incompatível para '{expected_field}'",
    ):
        get_or_create_knowledge_collection(
            client,
            name="knowledge-incompatible-test",
            schema_version=schema_version,
            embedding_model=embedding_model,
        )


@pytest.mark.parametrize(
    "name",
    [
        "",
        "   ",
    ],
)
def test_get_or_create_knowledge_collection_rejects_empty_name(
    tmp_path: Path,
    name: str,
) -> None:
    client = create_persistent_chroma_client(
        tmp_path,
    )

    with pytest.raises(
        ValueError,
        match="nome da coleção Chroma",
    ):
        get_or_create_knowledge_collection(
            client,
            name=name,
            schema_version=SCHEMA_VERSION,
            embedding_model=EMBEDDING_MODEL,
        )


@pytest.mark.parametrize(
    "schema_version",
    [
        0,
        -1,
    ],
)
def test_get_or_create_knowledge_collection_rejects_invalid_schema_version(
    tmp_path: Path,
    schema_version: int,
) -> None:
    client = create_persistent_chroma_client(
        tmp_path,
    )

    with pytest.raises(
        ValueError,
        match="maior que zero",
    ):
        get_or_create_knowledge_collection(
            client,
            name="knowledge-invalid-schema-test",
            schema_version=schema_version,
            embedding_model=EMBEDDING_MODEL,
        )


@pytest.mark.parametrize(
    "embedding_model",
    [
        "",
        "   ",
    ],
)
def test_get_or_create_knowledge_collection_rejects_empty_embedding_model(
    tmp_path: Path,
    embedding_model: str,
) -> None:
    client = create_persistent_chroma_client(
        tmp_path,
    )

    with pytest.raises(
        ValueError,
        match="modelo de embeddings",
    ):
        get_or_create_knowledge_collection(
            client,
            name="knowledge-empty-model-test",
            schema_version=SCHEMA_VERSION,
            embedding_model=embedding_model,
        )


def test_chroma_collection_persists_records_between_clients(
    tmp_path: Path,
) -> None:
    _, collection = create_collection(
        tmp_path,
        name="knowledge-persistence-test",
    )
    collection.upsert(
        ids=[
            "article-one",
        ],
        embeddings=[
            [1.0, 0.0],
        ],
        documents=[
            "Conteúdo sintético do artigo.",
        ],
        metadatas=[
            {
                "category": "teste",
                "schema_version": SCHEMA_VERSION,
            },
        ],
    )

    second_client = create_persistent_chroma_client(
        tmp_path,
    )
    persisted_collection = get_or_create_knowledge_collection(
        second_client,
        name="knowledge-persistence-test",
        schema_version=SCHEMA_VERSION,
        embedding_model=EMBEDDING_MODEL,
    )
    result = persisted_collection.get(
        ids=[
            "article-one",
        ],
    )

    assert persisted_collection.count() == 1
    assert result["ids"] == [
        "article-one",
    ]


def test_chroma_collection_uses_cosine_distance(
    tmp_path: Path,
) -> None:
    _, collection = create_collection(
        tmp_path,
        name="knowledge-cosine-test",
    )
    collection.upsert(
        ids=[
            "same-direction",
            "orthogonal",
        ],
        embeddings=[
            [1.0, 0.0],
            [0.0, 1.0],
        ],
        documents=[
            "Mesmo sentido.",
            "Ortogonal.",
        ],
    )

    result = collection.query(
        query_embeddings=[
            [1.0, 0.0],
        ],
        n_results=2,
    )

    assert result["ids"] == [
        [
            "same-direction",
            "orthogonal",
        ],
    ]
    assert result["distances"] is not None
    assert result["distances"][0][0] == pytest.approx(0.0)
    assert result["distances"][0][1] == pytest.approx(1.0)


def test_chroma_collection_requires_explicit_vectors(
    tmp_path: Path,
) -> None:
    _, collection = create_collection(
        tmp_path,
        name="knowledge-explicit-vectors-test",
    )
    embeddings: Sequence[Sequence[float]] = [
        [0.5, 0.5],
    ]

    collection.upsert(
        ids=[
            "article-with-explicit-vector",
        ],
        embeddings=embeddings,
        documents=[
            "Documento com vetor fornecido pela aplicação.",
        ],
    )

    result = collection.query(
        query_embeddings=[
            [0.5, 0.5],
        ],
        n_results=1,
    )

    assert result["ids"] == [
        [
            "article-with-explicit-vector",
        ],
    ]
