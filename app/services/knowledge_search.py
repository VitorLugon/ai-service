from typing import Protocol

from app.knowledge.vector_index import KnowledgeVectorIndex
from app.schemas.knowledge import KnowledgeSearchMatch


class TextEmbeddingProvider(Protocol):
    """Contrato mínimo para geração de embedding de texto."""

    async def embed_text(
        self,
        text: str,
    ) -> list[float]:
        """Gera o embedding de um texto."""


class KnowledgeSearchService:
    """Executa busca semântica na base de conhecimento."""

    def __init__(
        self,
        embedding_provider: TextEmbeddingProvider,
        index: KnowledgeVectorIndex,
    ) -> None:
        self._embedding_provider = embedding_provider
        self._index = index

    async def search(
        self,
        query: str,
        *,
        top_k: int = 3,
    ) -> list[KnowledgeSearchMatch]:
        """Busca os artigos semanticamente mais relevantes."""

        normalized_query = query.strip()

        if not normalized_query:
            raise ValueError(
                "A consulta não pode estar vazia.",
            )

        query_embedding = await self._embedding_provider.embed_text(
            normalized_query,
        )

        return self._index.search(
            query_embedding,
            top_k=top_k,
        )
