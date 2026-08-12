import math

import pytest
from pydantic import ValidationError

from app.schemas.rag import RagContext, RagSource
from app.schemas.tickets import TicketCategory


def valid_source(**overrides: object) -> RagSource:
    data: dict[str, object] = {
        "article_id": "recover-account-access",
        "title": "Recuperar acesso à conta",
        "category": TicketCategory.ACCESS_AND_AUTHENTICATION,
        "score": 0.87,
        "rank": 1,
        "content": "Conteúdo completo do artigo usado como evidência recuperada.",
    }
    data.update(
        overrides,
    )

    return RagSource(
        **data,
    )


def test_rag_source_accepts_valid_data() -> None:
    source = valid_source(
        article_id=" recover-account-access ",
        title=" Recuperar acesso à conta ",
        content=" Conteúdo completo do artigo usado como evidência recuperada. ",
    )

    assert source.article_id == "recover-account-access"
    assert source.title == "Recuperar acesso à conta"
    assert source.category is TicketCategory.ACCESS_AND_AUTHENTICATION
    assert source.score == 0.87
    assert source.rank == 1
    assert source.content == (
        "Conteúdo completo do artigo usado como evidência recuperada."
    )


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("article_id", "   "),
        ("title", "   "),
        ("content", "   "),
    ],
)
def test_rag_source_rejects_empty_strings(
    field_name: str,
    value: str,
) -> None:
    with pytest.raises(
        ValidationError,
    ):
        valid_source(
            **{field_name: value},
        )


@pytest.mark.parametrize(
    "rank",
    [
        0,
        -1,
    ],
)
def test_rag_source_rejects_invalid_rank(
    rank: int,
) -> None:
    with pytest.raises(
        ValidationError,
    ):
        valid_source(
            rank=rank,
        )


@pytest.mark.parametrize(
    "score",
    [
        1.01,
        -1.01,
        math.nan,
        math.inf,
        -math.inf,
    ],
)
def test_rag_source_rejects_invalid_score(
    score: float,
) -> None:
    with pytest.raises(
        ValidationError,
    ):
        valid_source(
            score=score,
        )


def test_rag_source_rejects_extra_field() -> None:
    with pytest.raises(
        ValidationError,
    ):
        valid_source(
            unexpected=True,
        )


def test_rag_context_accepts_valid_data() -> None:
    source = valid_source()
    context = RagContext(
        text="Texto de contexto.",
        sources=[
            source,
        ],
        source_count=1,
    )

    assert context.text == "Texto de contexto."
    assert context.sources == [
        source,
    ]
    assert context.source_count == 1


def test_rag_context_accepts_empty_context() -> None:
    context = RagContext(
        text="",
        sources=[],
        source_count=0,
    )

    assert context.text == ""
    assert context.sources == []
    assert context.source_count == 0


def test_rag_context_rejects_inconsistent_source_count() -> None:
    with pytest.raises(
        ValidationError,
    ):
        RagContext(
            text="Texto de contexto.",
            sources=[
                valid_source(),
            ],
            source_count=0,
        )


def test_rag_context_rejects_extra_field() -> None:
    with pytest.raises(
        ValidationError,
    ):
        RagContext(
            text="Texto de contexto.",
            sources=[],
            source_count=0,
            unexpected=True,
        )


def test_rag_objects_are_immutable() -> None:
    source = valid_source()
    context = RagContext(
        text="Texto de contexto.",
        sources=[
            source,
        ],
        source_count=1,
    )

    with pytest.raises(
        ValidationError,
    ):
        source.rank = 2

    with pytest.raises(
        ValidationError,
    ):
        context.source_count = 2
