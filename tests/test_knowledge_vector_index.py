import pytest

from app.knowledge.vector_index import KnowledgeVectorIndex
from app.schemas.knowledge import KnowledgeArticle
from app.schemas.tickets import TicketCategory


def create_article(
    article_id: str,
    title: str,
) -> KnowledgeArticle:
    """Cria um artigo válido para os testes."""

    return KnowledgeArticle(
        id=article_id,
        title=title,
        content=(
            "Este conteúdo possui tamanho suficiente para "
            "representar um artigo válido da base."
        ),
        category=TicketCategory.OTHER,
        keywords=["teste"],
    )


def test_vector_index_exposes_metadata() -> None:
    articles = [
        create_article(
            "article-one",
            "Primeiro artigo",
        ),
        create_article(
            "article-two",
            "Segundo artigo",
        ),
    ]

    index = KnowledgeVectorIndex(
        articles=articles,
        embeddings=[
            [1.0, 0.0],
            [0.0, 1.0],
        ],
    )

    assert index.size == 2
    assert index.dimensions == 2


def test_vector_index_orders_results_by_similarity() -> None:
    access_article = create_article(
        "access-article",
        "Recuperação de senha",
    )
    billing_article = create_article(
        "billing-article",
        "Revisão de fatura",
    )
    technical_article = create_article(
        "technical-article",
        "Erro no aplicativo",
    )

    index = KnowledgeVectorIndex(
        articles=[
            access_article,
            billing_article,
            technical_article,
        ],
        embeddings=[
            [1.0, 0.0],
            [0.0, 1.0],
            [0.6, 0.8],
        ],
    )

    results = index.search(
        [1.0, 0.0],
        top_k=2,
    )

    assert [result.article.id for result in results] == [
        "access-article",
        "technical-article",
    ]

    assert results[0].score == pytest.approx(1.0)
    assert results[1].score == pytest.approx(0.6)


def test_vector_index_uses_article_id_as_tie_breaker() -> None:
    index = KnowledgeVectorIndex(
        articles=[
            create_article(
                "second-article",
                "Segundo artigo",
            ),
            create_article(
                "first-article",
                "Primeiro artigo",
            ),
        ],
        embeddings=[
            [1.0, 0.0],
            [1.0, 0.0],
        ],
    )

    results = index.search(
        [1.0, 0.0],
        top_k=2,
    )

    assert [result.article.id for result in results] == [
        "first-article",
        "second-article",
    ]


def test_vector_index_returns_all_when_top_k_is_larger() -> None:
    index = KnowledgeVectorIndex(
        articles=[
            create_article(
                "only-article",
                "Único artigo",
            ),
        ],
        embeddings=[
            [1.0, 0.0],
        ],
    )

    results = index.search(
        [1.0, 0.0],
        top_k=10,
    )

    assert len(results) == 1


def test_vector_index_rejects_empty_articles() -> None:
    with pytest.raises(
        ValueError,
        match="ao menos um artigo",
    ):
        KnowledgeVectorIndex(
            articles=[],
            embeddings=[],
        )


def test_vector_index_rejects_different_counts() -> None:
    with pytest.raises(
        ValueError,
        match="quantidade de artigos",
    ):
        KnowledgeVectorIndex(
            articles=[
                create_article(
                    "article-one",
                    "Primeiro artigo",
                ),
            ],
            embeddings=[],
        )


def test_vector_index_rejects_duplicate_article_ids() -> None:
    with pytest.raises(
        ValueError,
        match="IDs de artigos duplicados",
    ):
        KnowledgeVectorIndex(
            articles=[
                create_article(
                    "duplicated",
                    "Primeiro artigo",
                ),
                create_article(
                    "duplicated",
                    "Segundo artigo",
                ),
            ],
            embeddings=[
                [1.0, 0.0],
                [0.0, 1.0],
            ],
        )


def test_vector_index_rejects_different_dimensions() -> None:
    with pytest.raises(
        ValueError,
        match="dimensões incompatíveis",
    ):
        KnowledgeVectorIndex(
            articles=[
                create_article(
                    "article-one",
                    "Primeiro artigo",
                ),
                create_article(
                    "article-two",
                    "Segundo artigo",
                ),
            ],
            embeddings=[
                [1.0, 0.0],
                [1.0, 0.0, 0.0],
            ],
        )


@pytest.mark.parametrize(
    "invalid_embedding",
    [
        [],
        [0.0, 0.0],
        [float("nan"), 0.0],
        [float("inf"), 0.0],
        [float("-inf"), 0.0],
    ],
)
def test_vector_index_rejects_invalid_embeddings(
    invalid_embedding: list[float],
) -> None:
    with pytest.raises(ValueError):
        KnowledgeVectorIndex(
            articles=[
                create_article(
                    "article-one",
                    "Primeiro artigo",
                ),
            ],
            embeddings=[
                invalid_embedding,
            ],
        )


def test_vector_index_rejects_invalid_query_dimensions() -> None:
    index = KnowledgeVectorIndex(
        articles=[
            create_article(
                "article-one",
                "Primeiro artigo",
            ),
        ],
        embeddings=[
            [1.0, 0.0],
        ],
    )

    with pytest.raises(
        ValueError,
        match="dimensões incompatíveis",
    ):
        index.search(
            [1.0, 0.0, 0.0],
        )


def test_vector_index_rejects_invalid_top_k() -> None:
    index = KnowledgeVectorIndex(
        articles=[
            create_article(
                "article-one",
                "Primeiro artigo",
            ),
        ],
        embeddings=[
            [1.0, 0.0],
        ],
    )

    with pytest.raises(
        ValueError,
        match="maior que zero",
    ):
        index.search(
            [1.0, 0.0],
            top_k=0,
        )
