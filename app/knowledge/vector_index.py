from collections.abc import Sequence
from math import isfinite

from app.core.vector_math import cosine_similarity
from app.schemas.knowledge import (
    KnowledgeArticle,
    KnowledgeSearchMatch,
)


def _normalize_embedding(
    embedding: Sequence[float],
    *,
    expected_dimensions: int | None = None,
) -> tuple[float, ...]:
    """Valida um embedding e cria uma cópia imutável."""

    normalized_embedding = tuple(float(value) for value in embedding)

    if not normalized_embedding:
        raise ValueError(
            "O embedding não pode estar vazio.",
        )

    if expected_dimensions is not None and (
        len(normalized_embedding) != expected_dimensions
    ):
        raise ValueError(
            "O embedding possui dimensões incompatíveis.",
        )

    if any(not isfinite(value) for value in normalized_embedding):
        raise ValueError(
            "O embedding contém valores não finitos.",
        )

    if all(value == 0.0 for value in normalized_embedding):
        raise ValueError(
            "O embedding não pode ser um vetor nulo.",
        )

    return normalized_embedding


class KnowledgeVectorIndex:
    """Índice vetorial em memória para artigos de conhecimento."""

    def __init__(
        self,
        articles: Sequence[KnowledgeArticle],
        embeddings: Sequence[Sequence[float]],
    ) -> None:
        if not articles:
            raise ValueError(
                "O índice deve possuir ao menos um artigo.",
            )

        if len(articles) != len(embeddings):
            raise ValueError(
                "A quantidade de artigos deve corresponder à quantidade de embeddings.",
            )

        article_ids = [article.id for article in articles]

        if len(article_ids) != len(set(article_ids)):
            raise ValueError(
                "O índice contém IDs de artigos duplicados.",
            )

        first_embedding = _normalize_embedding(
            embeddings[0],
        )
        dimensions = len(first_embedding)

        normalized_embeddings = [
            first_embedding,
            *[
                _normalize_embedding(
                    embedding,
                    expected_dimensions=dimensions,
                )
                for embedding in embeddings[1:]
            ],
        ]

        self._entries = tuple(
            zip(
                articles,
                normalized_embeddings,
                strict=True,
            ),
        )
        self._dimensions = dimensions

    @property
    def size(self) -> int:
        """Retorna a quantidade de artigos indexados."""

        return len(self._entries)

    @property
    def dimensions(self) -> int:
        """Retorna a dimensão dos embeddings."""

        return self._dimensions

    def search(
        self,
        query_embedding: Sequence[float],
        *,
        top_k: int = 3,
    ) -> list[KnowledgeSearchMatch]:
        """Retorna os artigos semanticamente mais próximos."""

        if top_k < 1:
            raise ValueError(
                "top_k deve ser maior que zero.",
            )

        normalized_query = _normalize_embedding(
            query_embedding,
            expected_dimensions=self._dimensions,
        )

        matches: list[KnowledgeSearchMatch] = []

        for article, article_embedding in self._entries:
            score = cosine_similarity(
                normalized_query,
                article_embedding,
            )

            # Evita pequenas ultrapassagens causadas por
            # arredondamento de ponto flutuante.
            normalized_score = max(
                -1.0,
                min(1.0, score),
            )

            matches.append(
                KnowledgeSearchMatch(
                    article=article,
                    score=normalized_score,
                ),
            )

        matches.sort(
            key=lambda match: (
                -match.score,
                match.article.id,
            ),
        )

        return matches[:top_k]
