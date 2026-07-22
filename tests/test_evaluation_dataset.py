import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.evaluation.dataset import (
    load_ticket_evaluation_cases,
)
from app.schemas.evaluation import TicketEvaluationCase


def write_dataset(
    path: Path,
    cases: list[dict[str, object]],
) -> None:
    """Grava um conjunto de avaliação temporário."""

    path.write_text(
        json.dumps(
            cases,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def create_raw_case(case_id: str) -> dict[str, object]:
    """Cria um caso em formato de dicionário."""

    return {
        "id": case_id,
        "ticket": {
            "title": "Erro de acesso",
            "description": ("Não consigo acessar minha conta com a senha atual."),
        },
        "expected_category": "acesso_e_autenticacao",
        "expected_priority": "alta",
        "rationale": ("O usuário está bloqueado e não informou alternativa."),
    }


def test_load_ticket_evaluation_cases(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "tickets.json"

    write_dataset(
        dataset_path,
        [create_raw_case("case-1")],
    )

    cases = load_ticket_evaluation_cases(
        dataset_path,
    )

    assert len(cases) == 1
    assert isinstance(cases[0], TicketEvaluationCase)
    assert cases[0].id == "case-1"
    assert cases[0].ticket.title == "Erro de acesso"
    assert cases[0].expected_category.value == "acesso_e_autenticacao"
    assert cases[0].expected_priority.value == "alta"


def test_dataset_rejects_duplicate_ids(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "tickets.json"

    write_dataset(
        dataset_path,
        [
            create_raw_case("duplicated"),
            create_raw_case("duplicated"),
        ],
    )

    with pytest.raises(
        ValueError,
        match="IDs duplicados",
    ):
        load_ticket_evaluation_cases(
            dataset_path,
        )


def test_dataset_rejects_invalid_schema(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "tickets.json"
    invalid_case = {
        **create_raw_case("invalid"),
        "expected_priority": "urgentissima",
    }

    write_dataset(
        dataset_path,
        [invalid_case],
    )

    with pytest.raises(ValidationError):
        load_ticket_evaluation_cases(
            dataset_path,
        )


def test_dataset_rejects_empty_list(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "tickets.json"

    write_dataset(dataset_path, [])

    with pytest.raises(
        ValueError,
        match="não pode estar vazio",
    ):
        load_ticket_evaluation_cases(
            dataset_path,
        )
