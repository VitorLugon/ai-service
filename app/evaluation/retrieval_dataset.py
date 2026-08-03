import json
from collections.abc import Collection
from pathlib import Path

from pydantic import TypeAdapter

from app.schemas.retrieval_evaluation import RetrievalEvaluationCase

_retrieval_cases_adapter = TypeAdapter(
    list[RetrievalEvaluationCase],
)


def load_retrieval_evaluation_cases(
    path: Path,
    *,
    known_article_ids: Collection[str],
) -> list[RetrievalEvaluationCase]:
    """Carrega e valida casos de avaliação de recuperação semântica."""

    raw_content = path.read_text(encoding="utf-8")
    raw_cases = json.loads(raw_content)

    cases = _retrieval_cases_adapter.validate_python(raw_cases)

    if not cases:
        raise ValueError(
            "O conjunto de avaliação de recuperação não pode estar vazio.",
        )

    case_ids = [case.id for case in cases]

    if len(case_ids) != len(set(case_ids)):
        raise ValueError(
            "O conjunto de avaliação de recuperação contém IDs duplicados.",
        )

    normalized_queries = [case.query.casefold() for case in cases]

    if len(normalized_queries) != len(set(normalized_queries)):
        raise ValueError(
            "O conjunto de avaliação de recuperação contém consultas duplicadas.",
        )

    unknown_article_ids = sorted(
        {
            article_id
            for case in cases
            for article_id in case.relevant_article_ids
            if article_id not in known_article_ids
        },
    )

    if unknown_article_ids:
        raise ValueError(
            "O dataset referencia artigos inexistentes: "
            + ", ".join(unknown_article_ids),
        )

    return cases
