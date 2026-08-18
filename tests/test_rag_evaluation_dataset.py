import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.evaluation.rag_dataset import load_rag_evaluation_cases
from app.knowledge.loader import load_knowledge_articles
from app.schemas.rag_evaluation import RagEvaluationCase, RagExpectedBehavior

DATASET_PATH = Path("evaluation/rag_cases.json")
KNOWLEDGE_BASE_PATH = Path("knowledge/articles.json")


def known_article_ids() -> set[str]:
    return {
        article.id
        for article in load_knowledge_articles(
            KNOWLEDGE_BASE_PATH,
        )
    }


def minimal_case(
    **overrides: object,
) -> dict[str, object]:
    data: dict[str, object] = {
        "id": "rag-test-case",
        "question": "Como recupero acesso à conta?",
        "relevant_article_ids": [
            "recover-account-access",
        ],
        "expected_answer_keywords": [
            "senha",
        ],
        "expected_behavior": "answer",
    }
    data.update(
        overrides,
    )

    return data


def write_cases(
    tmp_path: Path,
    cases: list[dict[str, object]],
) -> Path:
    path = tmp_path / "rag_cases.json"
    path.write_text(
        json.dumps(
            cases,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return path


def test_load_rag_evaluation_cases_loads_repository_dataset() -> None:
    cases = load_rag_evaluation_cases(
        DATASET_PATH,
        known_article_ids=known_article_ids(),
    )

    assert len(cases) == 16
    assert cases[0].id == "rag-recover-access"


def test_rag_evaluation_dataset_has_expected_distribution() -> None:
    cases = load_rag_evaluation_cases(
        DATASET_PATH,
        known_article_ids=known_article_ids(),
    )
    answer_cases = [
        case for case in cases if case.expected_behavior is RagExpectedBehavior.ANSWER
    ]
    no_evidence_cases = [
        case
        for case in cases
        if case.expected_behavior is RagExpectedBehavior.INSUFFICIENT_EVIDENCE
    ]
    multi_source_cases = [case for case in cases if len(case.relevant_article_ids) > 1]

    assert len(answer_cases) == 12
    assert len(no_evidence_cases) == 4
    assert len(multi_source_cases) == 2


def test_rag_evaluation_dataset_references_existing_articles() -> None:
    article_ids = known_article_ids()
    cases = load_rag_evaluation_cases(
        DATASET_PATH,
        known_article_ids=article_ids,
    )

    assert all(
        article_id in article_ids
        for case in cases
        for article_id in case.relevant_article_ids
    )


def test_rag_evaluation_case_normalizes_question_notes_and_keywords() -> None:
    case = RagEvaluationCase(
        id="rag-normalized",
        question="  Como recupero acesso?  ",
        relevant_article_ids=[
            "recover-account-access",
        ],
        expected_answer_keywords=[
            " Senha ",
            "senha",
            " LOGIN ",
        ],
        expected_behavior=RagExpectedBehavior.ANSWER,
        notes="  Observação  ",
    )

    assert case.question == "Como recupero acesso?"
    assert case.expected_answer_keywords == [
        "senha",
        "login",
    ]
    assert case.notes == "Observação"


def test_rag_evaluation_case_rejects_extra_field() -> None:
    with pytest.raises(
        ValidationError,
    ):
        RagEvaluationCase(
            **minimal_case(
                unexpected=True,
            ),
        )


def test_rag_evaluation_case_rejects_invalid_behavior() -> None:
    with pytest.raises(
        ValidationError,
    ):
        RagEvaluationCase(
            **minimal_case(
                expected_behavior="maybe",
            ),
        )


def test_rag_evaluation_case_rejects_empty_keywords() -> None:
    with pytest.raises(
        ValidationError,
    ):
        RagEvaluationCase(
            **minimal_case(
                expected_answer_keywords=[
                    "   ",
                ],
            ),
        )


def test_rag_evaluation_case_rejects_answer_without_relevant_article() -> None:
    with pytest.raises(
        ValidationError,
    ):
        RagEvaluationCase(
            **minimal_case(
                relevant_article_ids=[],
            ),
        )


def test_rag_evaluation_case_rejects_answer_without_keywords() -> None:
    with pytest.raises(
        ValidationError,
    ):
        RagEvaluationCase(
            **minimal_case(
                expected_answer_keywords=[],
            ),
        )


def test_rag_evaluation_case_rejects_no_evidence_with_relevant_article() -> None:
    with pytest.raises(
        ValidationError,
    ):
        RagEvaluationCase(
            **minimal_case(
                expected_behavior=RagExpectedBehavior.INSUFFICIENT_EVIDENCE,
                expected_answer_keywords=[],
            ),
        )


def test_rag_evaluation_case_rejects_duplicate_relevant_ids() -> None:
    with pytest.raises(
        ValidationError,
    ):
        RagEvaluationCase(
            **minimal_case(
                relevant_article_ids=[
                    "recover-account-access",
                    "recover-account-access",
                ],
            ),
        )


def test_load_rag_evaluation_cases_rejects_empty_dataset(tmp_path: Path) -> None:
    path = write_cases(
        tmp_path,
        [],
    )

    with pytest.raises(
        ValueError,
        match="não pode estar vazio",
    ):
        load_rag_evaluation_cases(
            path,
            known_article_ids=known_article_ids(),
        )


def test_load_rag_evaluation_cases_rejects_duplicate_ids(tmp_path: Path) -> None:
    path = write_cases(
        tmp_path,
        [
            minimal_case(id="rag-duplicate", question="Pergunta um?"),
            minimal_case(id="rag-duplicate", question="Pergunta dois?"),
        ],
    )

    with pytest.raises(
        ValueError,
        match="IDs duplicados",
    ):
        load_rag_evaluation_cases(
            path,
            known_article_ids=known_article_ids(),
        )


def test_load_rag_evaluation_cases_rejects_duplicate_questions(tmp_path: Path) -> None:
    path = write_cases(
        tmp_path,
        [
            minimal_case(id="rag-one", question="Pergunta repetida?"),
            minimal_case(id="rag-two", question="pergunta repetida?"),
        ],
    )

    with pytest.raises(
        ValueError,
        match="perguntas duplicadas",
    ):
        load_rag_evaluation_cases(
            path,
            known_article_ids=known_article_ids(),
        )


def test_load_rag_evaluation_cases_rejects_unknown_article(tmp_path: Path) -> None:
    path = write_cases(
        tmp_path,
        [
            minimal_case(
                relevant_article_ids=[
                    "unknown-article",
                ],
            ),
            minimal_case(
                id="rag-no-evidence",
                question="Qual é a política de férias?",
                relevant_article_ids=[],
                expected_answer_keywords=[],
                expected_behavior=RagExpectedBehavior.INSUFFICIENT_EVIDENCE,
            ),
        ],
    )

    with pytest.raises(
        ValueError,
        match="unknown-article",
    ):
        load_rag_evaluation_cases(
            path,
            known_article_ids=known_article_ids(),
        )


def test_load_rag_evaluation_cases_rejects_dataset_without_answer_case(
    tmp_path: Path,
) -> None:
    path = write_cases(
        tmp_path,
        [
            minimal_case(
                id="rag-no-evidence",
                question="Qual é a política de férias?",
                relevant_article_ids=[],
                expected_answer_keywords=[],
                expected_behavior=RagExpectedBehavior.INSUFFICIENT_EVIDENCE,
            ),
        ],
    )

    with pytest.raises(
        ValueError,
        match="resposta esperada",
    ):
        load_rag_evaluation_cases(
            path,
            known_article_ids=known_article_ids(),
        )


def test_load_rag_evaluation_cases_rejects_dataset_without_no_evidence_case(
    tmp_path: Path,
) -> None:
    path = write_cases(
        tmp_path,
        [
            minimal_case(),
        ],
    )

    with pytest.raises(
        ValueError,
        match="sem evidência",
    ):
        load_rag_evaluation_cases(
            path,
            known_article_ids=known_article_ids(),
        )
