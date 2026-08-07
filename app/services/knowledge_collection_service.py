from collections.abc import Mapping, Sequence
from typing import Protocol

from app.knowledge.indexing import build_knowledge_index_record
from app.schemas.knowledge import KnowledgeArticle
from app.schemas.knowledge_indexing import (
    KnowledgeDeletionResult,
    KnowledgeIndexingResult,
)
from app.services.knowledge_indexer import (
    ChromaMetadata,
    KnowledgeIndexEmbeddingProvider,
)


class KnowledgeArticleNotFoundError(RuntimeError):
    """Indica que um artigo não existe na coleção persistente."""


class KnowledgeCollectionMaintenanceCollection(Protocol):
    """Contrato mínimo para manutenção de registros no Chroma."""

    @property
    def name(self) -> str:
        """Retorna o nome da coleção."""

    def count(self) -> int:
        """Retorna a quantidade de registros persistidos."""

    def get(
        self,
        *,
        ids: Sequence[str],
    ) -> Mapping[str, object]:
        """Obtém registros por ID."""

    def upsert(
        self,
        *,
        ids: Sequence[str],
        embeddings: Sequence[Sequence[float]],
        documents: Sequence[str],
        metadatas: Sequence[ChromaMetadata],
    ) -> None:
        """Insere ou atualiza registros."""

    def delete(
        self,
        *,
        ids: Sequence[str],
    ) -> object:
        """Remove registros por ID."""


class KnowledgeCollectionService:
    """Mantém registros de conhecimento persistidos no Chroma."""

    def __init__(
        self,
        *,
        embedding_provider: KnowledgeIndexEmbeddingProvider,
        collection: KnowledgeCollectionMaintenanceCollection,
        schema_version: int,
    ) -> None:
        if schema_version <= 0:
            raise ValueError(
                "A versão do schema deve ser maior que zero.",
            )

        self._embedding_provider = embedding_provider
        self._collection = collection
        self._schema_version = schema_version

    async def update_article(
        self,
        article: KnowledgeArticle,
    ) -> KnowledgeIndexingResult:
        """Atualiza um artigo existente regenerando seu embedding."""

        if not collection_contains_id(
            self._collection,
            article.id,
        ):
            raise KnowledgeArticleNotFoundError(
                f"O artigo '{article.id}' não existe na coleção.",
            )

        record = build_knowledge_index_record(
            article,
            schema_version=self._schema_version,
            embedding_model=self._embedding_provider.model,
        )
        records_before = self._collection.count()
        embeddings = await self._embedding_provider.embed_texts(
            [
                record.embedding_text,
            ],
        )

        if len(embeddings) != 1 or len(embeddings[0]) < 1:
            raise ValueError(
                "A atualização deve gerar exatamente um embedding válido.",
            )

        self._collection.upsert(
            ids=[
                record.id,
            ],
            embeddings=embeddings,
            documents=[
                record.document,
            ],
            metadatas=[
                {
                    "title": record.metadata.title,
                    "category": record.metadata.category,
                    "keywords_json": record.metadata.keywords_json,
                    "schema_version": record.metadata.schema_version,
                    "embedding_model": record.metadata.embedding_model,
                },
            ],
        )

        records_after = self._collection.count()

        if records_after != records_before:
            raise RuntimeError(
                "A atualização alterou a quantidade de registros da coleção.",
            )

        if not collection_contains_id(
            self._collection,
            article.id,
        ):
            raise RuntimeError(
                "O artigo atualizado não foi encontrado na coleção.",
            )

        return KnowledgeIndexingResult(
            indexed_articles=1,
            collection_name=self._collection.name,
            records_before=records_before,
            records_after=records_after,
            embedding_dimensions=len(
                embeddings[0],
            ),
        )

    def delete_article(
        self,
        article_id: str,
    ) -> KnowledgeDeletionResult:
        """Remove um artigo existente da coleção persistente."""

        normalized_article_id = _validate_article_id(
            article_id,
        )

        if not collection_contains_id(
            self._collection,
            normalized_article_id,
        ):
            raise KnowledgeArticleNotFoundError(
                f"O artigo '{normalized_article_id}' não existe na coleção.",
            )

        records_before = self._collection.count()
        self._collection.delete(
            ids=[
                normalized_article_id,
            ],
        )
        records_after = self._collection.count()

        if collection_contains_id(
            self._collection,
            normalized_article_id,
        ):
            raise RuntimeError(
                "O artigo removido ainda existe na coleção.",
            )

        if records_after != records_before - 1:
            raise RuntimeError(
                "A remoção não reduziu a quantidade de registros em 1.",
            )

        return KnowledgeDeletionResult(
            deleted_article_id=normalized_article_id,
            collection_name=self._collection.name,
            records_before=records_before,
            records_after=records_after,
        )


def collection_contains_id(
    collection: KnowledgeCollectionMaintenanceCollection,
    article_id: str,
) -> bool:
    """Verifica se a coleção contém um ID sem depender de exceções."""

    normalized_article_id = _validate_article_id(
        article_id,
    )
    result = collection.get(
        ids=[
            normalized_article_id,
        ],
    )
    ids = result.get(
        "ids",
    )

    if not isinstance(
        ids,
        list,
    ):
        raise RuntimeError(
            "A resposta do Chroma para get(ids=...) é inválida.",
        )

    return normalized_article_id in ids


def _validate_article_id(
    article_id: str,
) -> str:
    normalized_article_id = article_id.strip()

    if not normalized_article_id:
        raise ValueError(
            "O ID do artigo não pode estar vazio.",
        )

    return normalized_article_id
