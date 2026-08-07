from collections.abc import Sequence
from decimal import Decimal

import tiktoken

FALLBACK_ENCODING_NAME = "cl100k_base"


def count_embedding_tokens(
    texts: Sequence[str],
    *,
    model: str,
) -> int:
    """Conta tokens de uma sequência de textos para estimar embeddings."""

    if isinstance(texts, str):
        raise TypeError(
            "Informe uma sequência de textos, não uma string única.",
        )

    normalized_texts = [text.strip() for text in texts]

    if not normalized_texts:
        raise ValueError(
            "É necessário informar ao menos um texto.",
        )

    if any(not text for text in normalized_texts):
        raise ValueError(
            "Os textos não podem estar vazios.",
        )

    try:
        encoding = tiktoken.encoding_for_model(
            model,
        )
    except KeyError:
        encoding = tiktoken.get_encoding(
            FALLBACK_ENCODING_NAME,
        )

    return sum(
        len(
            encoding.encode(
                text,
            ),
        )
        for text in normalized_texts
    )


def estimate_embedding_cost_usd(
    token_count: int,
    *,
    cost_per_million_tokens_usd: Decimal,
) -> Decimal:
    """Estima o custo de embeddings a partir da contagem de tokens."""

    if token_count < 0:
        raise ValueError(
            "A quantidade de tokens não pode ser negativa.",
        )

    if cost_per_million_tokens_usd < 0:
        raise ValueError(
            "O custo por milhão de tokens não pode ser negativo.",
        )

    return (
        Decimal(token_count)
        / Decimal(
            1_000_000,
        )
        * cost_per_million_tokens_usd
    )
