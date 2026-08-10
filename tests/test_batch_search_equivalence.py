from pathlib import Path

import pytest

from tests.test_vector_backends_equivalence import create_backends


def test_chroma_batch_search_matches_individual_searches(
    tmp_path: Path,
) -> None:
    _, chroma_backend = create_backends(
        tmp_path,
    )
    query_embeddings = [
        [
            1.0,
            0.0,
        ],
        [
            0.0,
            1.0,
        ],
        [
            -1.0,
            0.0,
        ],
    ]

    batch_results = chroma_backend.search_many(
        query_embeddings,
        top_k=3,
    )
    individual_results = [
        chroma_backend.search(
            query_embedding,
            top_k=3,
        )
        for query_embedding in query_embeddings
    ]

    assert len(batch_results) == len(query_embeddings)

    for batch_ranking, individual_ranking in zip(
        batch_results,
        individual_results,
        strict=True,
    ):
        assert [match.article.id for match in batch_ranking] == [
            match.article.id for match in individual_ranking
        ]

        for batch_match, individual_match in zip(
            batch_ranking,
            individual_ranking,
            strict=True,
        ):
            assert batch_match.score == pytest.approx(
                individual_match.score,
                abs=1e-6,
            )
