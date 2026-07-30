from collections.abc import Sequence
from math import sqrt


def cosine_similarity(
    left: Sequence[float],
    right: Sequence[float],
) -> float:
    """Calcula a similaridade de cosseno entre dois vetores."""

    if not left or not right:
        raise ValueError("Os vetores não podem estar vazios.")

    if len(left) != len(right):
        raise ValueError(
            "Os vetores devem possuir o mesmo tamanho.",
        )

    dot_product = sum(
        left_value * right_value
        for left_value, right_value in zip(
            left,
            right,
            strict=True,
        )
    )

    left_norm = sqrt(
        sum(value * value for value in left),
    )
    right_norm = sqrt(
        sum(value * value for value in right),
    )

    if left_norm == 0 or right_norm == 0:
        raise ValueError(
            "Não é possível comparar um vetor nulo.",
        )

    return dot_product / (left_norm * right_norm)
