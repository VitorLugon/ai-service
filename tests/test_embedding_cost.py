from decimal import Decimal

import pytest

from app.services.embedding_cost import (
    count_embedding_tokens,
    estimate_embedding_cost_usd,
)


def test_count_embedding_tokens_is_deterministic() -> None:
    texts = [
        "Recuperar senha de acesso.",
        "Erro técnico no painel.",
    ]

    first_count = count_embedding_tokens(
        texts,
        model="text-embedding-3-small",
    )
    second_count = count_embedding_tokens(
        texts,
        model="text-embedding-3-small",
    )

    assert first_count == second_count
    assert first_count > 0
    assert texts == [
        "Recuperar senha de acesso.",
        "Erro técnico no painel.",
    ]


def test_count_embedding_tokens_uses_explicit_fallback_for_unknown_model() -> None:
    token_count = count_embedding_tokens(
        [
            "Texto para modelo desconhecido.",
        ],
        model="unknown-embedding-model",
    )

    assert token_count > 0


@pytest.mark.parametrize(
    "texts",
    [
        [],
        [
            "   ",
        ],
    ],
)
def test_count_embedding_tokens_rejects_invalid_batches(
    texts: list[str],
) -> None:
    with pytest.raises(
        ValueError,
    ):
        count_embedding_tokens(
            texts,
            model="text-embedding-3-small",
        )


def test_count_embedding_tokens_rejects_single_string() -> None:
    with pytest.raises(
        TypeError,
        match="string única",
    ):
        count_embedding_tokens(
            "texto isolado",
            model="text-embedding-3-small",
        )


def test_estimate_embedding_cost_usd_uses_decimal() -> None:
    cost = estimate_embedding_cost_usd(
        500_000,
        cost_per_million_tokens_usd=Decimal("0.02"),
    )

    assert cost == Decimal("0.010")


@pytest.mark.parametrize(
    ("token_count", "cost_per_million"),
    [
        (-1, Decimal("0.02")),
        (1, Decimal("-0.01")),
    ],
)
def test_estimate_embedding_cost_usd_rejects_invalid_inputs(
    token_count: int,
    cost_per_million: Decimal,
) -> None:
    with pytest.raises(
        ValueError,
    ):
        estimate_embedding_cost_usd(
            token_count,
            cost_per_million_tokens_usd=cost_per_million,
        )
