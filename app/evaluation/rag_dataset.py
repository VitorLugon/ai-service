import json
from collections.abc import Collection
from pathlib import Path

from pydantic import TypeAdapter

from app.schemas.rag_evaluation import RagEvaluationCase, RagExpectedBehavior

_rag_cases_adapter = TypeAdapter(
    list[RagEvaluationCase],
)


def load_rag_evaluation_cases(
    path: Path,
    *,
    known_article_ids: Collection[str],
) -> list[RagEvaluationCase]:
    """Carrega e valida casos sintéticos de avaliação RAG."""

    raw_content = path.read_text(
        encoding="utf-8",
    )
    raw_cases = json.loads(
        raw_content,
    )

    cases = _rag_cases_adapter.validate_python(
        raw_cases,
    )

    if not cases:
        raise ValueError(
            "O conjunto de avaliação RAG não pode estar vazio.",
        )

    case_ids = [case.id for case in cases]

    if len(case_ids) != len(set(case_ids)):
        raise ValueError(
            "O conjunto de avaliação RAG contém IDs duplicados.",
        )

    normalized_questions = [case.question.casefold() for case in cases]

    if len(normalized_questions) != len(set(normalized_questions)):
        raise ValueError(
            "O conjunto de avaliação RAG contém perguntas duplicadas.",
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
            "O dataset RAG referencia artigos inexistentes: "
            + ", ".join(
                unknown_article_ids,
            ),
        )

    if not any(case.expected_behavior is RagExpectedBehavior.ANSWER for case in cases):
        raise ValueError(
            "O dataset RAG deve possuir ao menos um caso com resposta esperada.",
        )

    if not any(
        case.expected_behavior is RagExpectedBehavior.INSUFFICIENT_EVIDENCE
        for case in cases
    ):
        raise ValueError(
            "O dataset RAG deve possuir ao menos um caso sem evidência.",
        )

    return cases
