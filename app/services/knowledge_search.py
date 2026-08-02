from collections.abc import Sequence
from typing import Protocol

from app.knowledge.text import build_knowledge_article_embedding_text
from app.knowledge.vector_index import KnowledgeVectorIndex
from app.schemas.knowledge import (
    KnowledgeArticle,
    KnowledgeSearchMatch,
)


class EmbeddingProvider(Protocol):
    """Contrato usado pela busca e pela construção do índice."""

    @property
    def model(self) -> str:
        """Retorna o modelo de embeddings."""

    async def embed_text(
        self,
        text: str,
    ) -> list[float]:
        """Gera o embedding de um texto."""

    async def embed_texts(
        self,
        texts: Sequence[str],
    ) -> list[list[float]]:
        """Gera embeddings para vários textos."""


class KnowledgeSearchService:
    """Executa busca semântica na base de conhecimento."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        index: KnowledgeVectorIndex,
    ) -> None:
        self._embedding_provider = embedding_provider
        self._index = index

    @property
    def model(self) -> str:
        """Retorna o modelo utilizado pela busca."""

        return self._embedding_provider.model

    @property
    def indexed_articles(self) -> int:
        """Retorna a quantidade de artigos indexados."""

        return self._index.size

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


async def build_knowledge_search_service(
    articles: Sequence[KnowledgeArticle],
    embedding_provider: EmbeddingProvider,
) -> KnowledgeSearchService:
    """Gera os embeddings dos artigos e constrói a busca."""

    if not articles:
        raise ValueError(
            "É necessário informar ao menos um artigo.",
        )

    article_texts = [
        build_knowledge_article_embedding_text(
            article,
        )
        for article in articles
    ]

    article_embeddings = await embedding_provider.embed_texts(
        article_texts,
    )

    index = KnowledgeVectorIndex(
        articles=articles,
        embeddings=article_embeddings,
    )

    return KnowledgeSearchService(
        embedding_provider=embedding_provider,
        index=index,
    )
