from typing import cast

from chromadb.errors import ChromaError, NotFoundError

from app.core.config import Settings
from app.core.exceptions import (
    KnowledgeBaseNotIndexedError,
    KnowledgeStoreConfigurationError,
    KnowledgeStoreUnavailableError,
)
from app.knowledge.chroma import (
    create_persistent_chroma_client,
    get_existing_knowledge_collection,
)
from app.knowledge.chroma_backend import (
    ChromaKnowledgeCollection,
    ChromaKnowledgeSearchBackend,
)

INDEX_KNOWLEDGE_BASE_COMMAND = "python -m scripts.index_knowledge_base"


def load_persisted_knowledge_backend(
    settings: Settings,
) -> ChromaKnowledgeSearchBackend:
    """Carrega o backend Chroma persistente já indexado."""

    client = create_persistent_chroma_client(
        settings.chroma_persist_directory,
    )

    try:
        collection = get_existing_knowledge_collection(
            client,
            name=settings.chroma_collection_name,
            schema_version=settings.chroma_schema_version,
            embedding_model=settings.openai_embedding_model,
        )
    except NotFoundError as error:
        raise KnowledgeBaseNotIndexedError(
            "A base de conhecimento persistente não foi encontrada. "
            f"Execute {INDEX_KNOWLEDGE_BASE_COMMAND} antes de iniciar a API.",
        ) from error
    except ChromaError as error:
        raise KnowledgeStoreUnavailableError(
            "Não foi possível abrir a coleção de conhecimento persistente.",
        ) from error
    except ValueError as error:
        raise KnowledgeStoreConfigurationError(
            "A coleção de conhecimento foi criada com configuração incompatível "
            "e precisa ser reindexada.",
        ) from error

    try:
        record_count = collection.count()
    except ChromaError as error:
        raise KnowledgeStoreUnavailableError(
            "Não foi possível consultar a contagem da coleção de conhecimento.",
        ) from error

    if record_count <= 0:
        raise KnowledgeBaseNotIndexedError(
            "A coleção de conhecimento está vazia. "
            f"Execute {INDEX_KNOWLEDGE_BASE_COMMAND}.",
        )

    return ChromaKnowledgeSearchBackend(
        cast(
            ChromaKnowledgeCollection,
            collection,
        ),
    )
