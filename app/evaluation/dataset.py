import json
from pathlib import Path

from pydantic import TypeAdapter

from app.schemas.evaluation import TicketEvaluationCase

_cases_adapter = TypeAdapter(list[TicketEvaluationCase])


def load_ticket_evaluation_cases(
    path: Path,
) -> list[TicketEvaluationCase]:
    """Carrega e valida os casos de avaliação."""

    raw_content = path.read_text(encoding="utf-8")
    raw_cases = json.loads(raw_content)

    cases = _cases_adapter.validate_python(raw_cases)

    if not cases:
        raise ValueError(
            "O conjunto de avaliação não pode estar vazio.",
        )

    case_ids = [case.id for case in cases]

    if len(case_ids) != len(set(case_ids)):
        raise ValueError(
            "O conjunto de avaliação contém IDs duplicados.",
        )

    return cases
