import pytest

from app.core.vector_math import cosine_similarity


def test_cosine_similarity_returns_one_for_equal_vectors() -> None:
    similarity = cosine_similarity(
        [1.0, 2.0, 3.0],
        [1.0, 2.0, 3.0],
    )

    assert similarity == pytest.approx(1.0)


def test_cosine_similarity_returns_zero_for_orthogonal_vectors() -> None:
    similarity = cosine_similarity(
        [1.0, 0.0],
        [0.0, 1.0],
    )

    assert similarity == pytest.approx(0.0)


def test_cosine_similarity_returns_negative_for_opposite_vectors() -> None:
    similarity = cosine_similarity(
        [1.0, 0.0],
        [-1.0, 0.0],
    )

    assert similarity == pytest.approx(-1.0)


def test_cosine_similarity_rejects_different_dimensions() -> None:
    with pytest.raises(ValueError, match="mesmo tamanho"):
        cosine_similarity(
            [1.0, 2.0],
            [1.0],
        )


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ([], []),
        ([1.0], []),
        ([], [1.0]),
    ],
)
def test_cosine_similarity_rejects_empty_vectors(
    left: list[float],
    right: list[float],
) -> None:
    with pytest.raises(ValueError, match="não podem estar vazios"):
        cosine_similarity(left, right)


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ([0.0, 0.0], [1.0, 1.0]),
        ([1.0, 1.0], [0.0, 0.0]),
    ],
)
def test_cosine_similarity_rejects_zero_vectors(
    left: list[float],
    right: list[float],
) -> None:
    with pytest.raises(ValueError, match="vetor nulo"):
        cosine_similarity(left, right)
