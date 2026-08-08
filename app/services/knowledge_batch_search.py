from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from app.schemas.knowledge import (
    MAX_KNOWLEDGE_BATCH_QUERIES,
    KnowledgeBatchSearchItem,
    KnowledgeBatchSearchResponse,
    KnowledgeSearchFilter,
    KnowledgeSearchMatch,
)
from app.services.knowledge_search import EmbeddingProvider


@runtime_checkable
class BatchKnowledgeSearchBackend(Protocol):
    """Capacidade de busca vetorial em lote."""

    @property
    def size(self) -> int:
        """Retorna a quantidade de artigos disponíveis."""

    def search_many(
        self,
        query_embeddings: Sequence[Sequence[float]],
        *,
        top_k: int = 3,
        search_filter: KnowledgeSearchFilter | None = None,
    ) -> list[list[KnowledgeSearchMatch]]:
        """Busca resultados para múltiplos embeddings de consulta."""


class KnowledgeBatchSearchService:
    """Executa busca semântica em lote."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        backend: BatchKnowledgeSearchBackend,
    ) -> None:
        self._embedding_provider = embedding_provider
        self._backend = backend

    @property
    def model(self) -> str:
        """Retorna o modelo utilizado pela busca."""

        return self._embedding_provider.model

    @property
    def indexed_articles(self) -> int:
        """Retorna a quantidade de artigos indexados."""

        return self._backend.size

    async def search_many(
        self,
        queries: Sequence[str],
        *,
        top_k: int = 3,
        search_filter: KnowledgeSearchFilter | None = None,
    ) -> KnowledgeBatchSearchResponse:
        """Busca artigos semanticamente relevantes para várias queries."""

        normalized_queries = _normalize_queries(
            queries,
        )

        query_embeddings = await self._embedding_provider.embed_texts(
            normalized_queries,
        )

        if len(query_embeddings) != len(normalized_queries):
            raise ValueError(
                "A quantidade de embeddings deve corresponder ao lote de consultas.",
            )

        rankings = self._backend.search_many(
            query_embeddings,
            top_k=top_k,
            search_filter=search_filter,
        )

        if len(rankings) != len(normalized_queries):
            raise ValueError(
                "A quantidade de rankings deve corresponder ao lote de consultas.",
            )

        return KnowledgeBatchSearchResponse(
            model=self.model,
            indexed_articles=self.indexed_articles,
            results=[
                KnowledgeBatchSearchItem(
                    query=query,
                    matches=matches,
                )
                for query, matches in zip(
                    normalized_queries,
                    rankings,
                    strict=True,
                )
            ],
        )


def _normalize_queries(
    queries: Sequence[str],
) -> list[str]:
    if isinstance(
        queries,
        str,
    ):
        raise TypeError(
            "O lote de consultas deve ser uma sequência de textos.",
        )

    if not queries:
        raise ValueError(
            "É necessário informar ao menos uma consulta.",
        )

    if len(queries) > MAX_KNOWLEDGE_BATCH_QUERIES:
        raise ValueError(
            "O lote de consultas deve possuir no máximo "
            f"{MAX_KNOWLEDGE_BATCH_QUERIES} itens.",
        )

    normalized_queries: list[str] = []

    for query in queries:
        normalized_query = query.strip()

        if not normalized_query:
            raise ValueError(
                "As consultas não podem estar vazias.",
            )

        normalized_queries.append(
            normalized_query,
        )

    return normalized_queries
