import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.evaluation.retrieval_dataset import (
    load_retrieval_evaluation_cases,
)
from app.knowledge.loader import load_knowledge_articles
from app.schemas.retrieval_evaluation import RetrievalEvaluationCase


def valid_case(
    case_id: str = "access-01",
    query: str = "  Recuperar senha  ",
    relevant_article_ids: list[str] | None = None,
) -> dict[str, object]:
    """Cria um caso válido serializável."""

    return {
        "id": case_id,
        "query": query,
        "relevant_article_ids": (
            [
                "recover-account-access",
            ]
            if relevant_article_ids is None
            else relevant_article_ids
        ),
    }


def write_json(
    path: Path,
    data: object,
) -> None:
    """Escreve JSON em UTF-8 preservando acentos."""

    path.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def load_cases(
    path: Path,
    *,
    known_article_ids: set[str] | None = None,
) -> list[RetrievalEvaluationCase]:
    """Carrega casos com um conjunto padrão de artigos conhecidos."""

    return load_retrieval_evaluation_cases(
        path,
        known_article_ids=known_article_ids
        or {
            "recover-account-access",
            "configure-multi-factor-authentication",
        },
    )


def test_load_retrieval_evaluation_cases_returns_valid_cases(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "queries.json"
    write_json(
        dataset_path,
        [
            valid_case("access-01", "  Recuperar senha  "),
            valid_case(
                "access-02",
                "Configurar MFA",
                [
                    "configure-multi-factor-authentication",
                ],
            ),
        ],
    )

    cases = load_cases(dataset_path)

    assert [case.id for case in cases] == [
        "access-01",
        "access-02",
    ]
    assert all(isinstance(case, RetrievalEvaluationCase) for case in cases)
    assert cases[0].query == "Recuperar senha"
    assert cases[1].relevant_article_ids == [
        "configure-multi-factor-authentication",
    ]


def test_load_retrieval_evaluation_cases_rejects_empty_dataset(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "queries.json"
    write_json(
        dataset_path,
        [],
    )

    with pytest.raises(
        ValueError,
        match="não pode estar vazio",
    ):
        load_cases(dataset_path)


def test_load_retrieval_evaluation_cases_rejects_duplicate_case_ids(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "queries.json"
    write_json(
        dataset_path,
        [
            valid_case("access-01", "Recuperar senha"),
            valid_case("access-01", "Configurar MFA"),
        ],
    )

    with pytest.raises(
        ValueError,
        match="IDs duplicados",
    ):
        load_cases(dataset_path)


def test_load_retrieval_evaluation_cases_rejects_duplicate_queries(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "queries.json"
    write_json(
        dataset_path,
        [
            valid_case("access-01", "Recuperar senha"),
            valid_case("access-02", "  Recuperar senha  "),
        ],
    )

    with pytest.raises(
        ValueError,
        match="consultas duplicadas",
    ):
        load_cases(dataset_path)


def test_load_retrieval_evaluation_cases_rejects_case_insensitive_queries(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "queries.json"
    write_json(
        dataset_path,
        [
            valid_case("access-01", "Recuperar senha"),
            valid_case("access-02", "recuperar senha"),
        ],
    )

    with pytest.raises(
        ValueError,
        match="consultas duplicadas",
    ):
        load_cases(dataset_path)


def test_load_retrieval_evaluation_cases_rejects_empty_relevant_ids(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "queries.json"
    write_json(
        dataset_path,
        [
            valid_case(
                relevant_article_ids=[],
            ),
        ],
    )

    with pytest.raises(ValidationError):
        load_cases(dataset_path)


def test_load_retrieval_evaluation_cases_rejects_duplicate_relevant_ids(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "queries.json"
    write_json(
        dataset_path,
        [
            valid_case(
                relevant_article_ids=[
                    "recover-account-access",
                    "recover-account-access",
                ],
            ),
        ],
    )

    with pytest.raises(
        ValidationError,
        match="duplicatas",
    ):
        load_cases(dataset_path)


def test_load_retrieval_evaluation_cases_rejects_unknown_articles(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "queries.json"
    write_json(
        dataset_path,
        [
            valid_case(
                relevant_article_ids=[
                    "unknown-article",
                ],
            ),
        ],
    )

    with pytest.raises(
        ValueError,
        match="artigos inexistentes: unknown-article",
    ):
        load_cases(dataset_path)


def test_unknown_article_message_is_deterministic(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "queries.json"
    write_json(
        dataset_path,
        [
            valid_case(
                relevant_article_ids=[
                    "unknown-b",
                    "unknown-a",
                ],
            ),
        ],
    )

    with pytest.raises(
        ValueError,
        match="unknown-a, unknown-b",
    ):
        load_cases(dataset_path)


def test_load_retrieval_evaluation_cases_rejects_invalid_schema(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "queries.json"
    write_json(
        dataset_path,
        [
            {
                "id": "invalid id",
                "query": "Recuperar senha",
                "relevant_article_ids": [
                    "recover-account-access",
                ],
            },
        ],
    )

    with pytest.raises(ValidationError):
        load_cases(dataset_path)


def test_load_retrieval_evaluation_cases_rejects_extra_fields(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "queries.json"
    case = valid_case()
    case["unexpected"] = True
    write_json(
        dataset_path,
        [
            case,
        ],
    )

    with pytest.raises(ValidationError):
        load_cases(dataset_path)


def test_load_retrieval_evaluation_cases_preserves_json_error(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "queries.json"
    dataset_path.write_text(
        "{",
        encoding="utf-8",
    )

    with pytest.raises(json.JSONDecodeError):
        load_cases(dataset_path)


def test_load_retrieval_evaluation_cases_preserves_file_not_found(
    tmp_path: Path,
) -> None:
    with pytest.raises(FileNotFoundError):
        load_cases(
            tmp_path / "missing.json",
        )


def test_repository_retrieval_dataset_is_valid() -> None:
    project_root = Path(__file__).resolve().parents[1]
    articles = load_knowledge_articles(
        project_root / "knowledge" / "articles.json",
    )
    known_article_ids = {article.id for article in articles}

    cases = load_retrieval_evaluation_cases(
        project_root / "evaluation" / "knowledge_queries.json",
        known_article_ids=known_article_ids,
    )

    case_ids = [case.id for case in cases]
    queries = [case.query.casefold() for case in cases]
    relevance_counts = [len(case.relevant_article_ids) for case in cases]
    represented_article_ids = {
        article_id for case in cases for article_id in case.relevant_article_ids
    }

    assert len(cases) == 18
    assert len(case_ids) == len(set(case_ids))
    assert len(queries) == len(set(queries))
    assert relevance_counts.count(1) == 12
    assert relevance_counts.count(2) == 6
    assert represented_article_ids == known_article_ids
