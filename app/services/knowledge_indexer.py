from collections.abc import Mapping, Sequence
from math import isfinite
from typing import Protocol

from app.knowledge.indexing import build_knowledge_index_records
from app.schemas.knowledge import KnowledgeArticle
from app.schemas.knowledge_indexing import (
    KnowledgeIndexingResult,
    KnowledgeIndexRecord,
)

ChromaMetadataValue = str | int | float | bool
ChromaMetadata = Mapping[str, ChromaMetadataValue]


class KnowledgeIndexEmbeddingProvider(Protocol):
    """Contrato mínimo para gerar embeddings em lote."""

    @property
    def model(self) -> str:
        """Retorna o modelo de embeddings."""

    async def embed_texts(
        self,
        texts: Sequence[str],
    ) -> list[list[float]]:
        """Gera embeddings para vários textos."""


class KnowledgeIndexCollection(Protocol):
    """Contrato mínimo de escrita usado pelo indexador Chroma."""

    @property
    def name(self) -> str:
        """Retorna o nome da coleção."""

    def count(self) -> int:
        """Retorna a quantidade de registros persistidos."""

    def upsert(
        self,
        *,
        ids: Sequence[str],
        embeddings: Sequence[Sequence[float]],
        documents: Sequence[str],
        metadatas: Sequence[ChromaMetadata],
    ) -> None:
        """Insere ou atualiza registros preservando IDs estáveis."""


class KnowledgeIndexer:
    """Indexa artigos de conhecimento no Chroma de forma idempotente."""

    def __init__(
        self,
        *,
        embedding_provider: KnowledgeIndexEmbeddingProvider,
        collection: KnowledgeIndexCollection,
        schema_version: int,
    ) -> None:
        if schema_version <= 0:
            raise ValueError(
                "A versão do schema deve ser maior que zero.",
            )

        self._embedding_provider = embedding_provider
        self._collection = collection
        self._schema_version = schema_version

    async def index(
        self,
        articles: Sequence[KnowledgeArticle],
    ) -> KnowledgeIndexingResult:
        """Gera embeddings em lote e persiste os artigos com upsert."""

        records = build_knowledge_index_records(
            articles,
            schema_version=self._schema_version,
            embedding_model=self._embedding_provider.model,
        )
        embedding_texts = [record.embedding_text for record in records]
        records_before = self._collection.count()
        embeddings = await self._embedding_provider.embed_texts(
            embedding_texts,
        )
        embedding_dimensions = _validate_embeddings(
            embeddings,
            expected_count=len(records),
        )

        self._collection.upsert(
            ids=[record.id for record in records],
            embeddings=embeddings,
            documents=[record.document for record in records],
            metadatas=[
                _metadata_for_chroma(
                    record,
                )
                for record in records
            ],
        )

        return KnowledgeIndexingResult(
            indexed_articles=len(records),
            collection_name=self._collection.name,
            records_before=records_before,
            records_after=self._collection.count(),
            embedding_dimensions=embedding_dimensions,
        )


def _metadata_for_chroma(
    record: KnowledgeIndexRecord,
) -> dict[str, ChromaMetadataValue]:
    return {
        "title": record.metadata.title,
        "category": record.metadata.category,
        "keywords_json": record.metadata.keywords_json,
        "schema_version": record.metadata.schema_version,
        "embedding_model": record.metadata.embedding_model,
    }


def _validate_embeddings(
    embeddings: Sequence[Sequence[float]],
    *,
    expected_count: int,
) -> int:
    if len(embeddings) != expected_count:
        raise ValueError(
            "A quantidade de embeddings não corresponde aos registros.",
        )

    normalized_embeddings = [
        tuple(float(value) for value in embedding) for embedding in embeddings
    ]

    if any(not embedding for embedding in normalized_embeddings):
        raise ValueError(
            "Os embeddings não podem estar vazios.",
        )

    dimensions = {len(embedding) for embedding in normalized_embeddings}

    if len(dimensions) != 1:
        raise ValueError(
            "Os embeddings possuem dimensões inconsistentes.",
        )

    if any(
        not isfinite(value)
        for embedding in normalized_embeddings
        for value in embedding
    ):
        raise ValueError(
            "Os embeddings contêm valores não finitos.",
        )

    return dimensions.pop()
