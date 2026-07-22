import asyncio

import pytest

from app.schemas.evaluation import TicketEvaluationCase
from app.schemas.tickets import (
    TicketCategory,
    TicketClassificationInput,
    TicketClassificationResult,
    TicketPriority,
)
from app.services.ticket_evaluator import TicketEvaluatorService


class FakeTicketClassifier:
    """Classificador previsível usado nos testes."""

    model = "test-model"

    def __init__(
        self,
        predictions: list[TicketClassificationResult],
    ) -> None:
        self._predictions = iter(predictions)

    async def classify(
        self,
        _: TicketClassificationInput,
    ) -> TicketClassificationResult:
        """Retorna a próxima classificação configurada."""

        return next(self._predictions)


def create_case(
    case_id: str,
    category: TicketCategory,
    priority: TicketPriority,
) -> TicketEvaluationCase:
    """Cria um caso de avaliação válido."""

    return TicketEvaluationCase(
        id=case_id,
        ticket=TicketClassificationInput(
            title="Chamado de exemplo",
            description=("Descrição suficientemente longa para o chamado."),
        ),
        expected_category=category,
        expected_priority=priority,
        rationale=("Classificação definida para validar as métricas."),
    )


def test_ticket_evaluator_calculates_accuracy() -> None:
    cases = [
        create_case(
            "case-1",
            TicketCategory.TECHNICAL_ERROR,
            TicketPriority.HIGH,
        ),
        create_case(
            "case-2",
            TicketCategory.BILLING,
            TicketPriority.MEDIUM,
        ),
    ]

    classifier = FakeTicketClassifier(
        predictions=[
            TicketClassificationResult(
                category=TicketCategory.TECHNICAL_ERROR,
                priority=TicketPriority.MEDIUM,
                summary="Foi identificado um erro técnico no sistema.",
                suggested_tags=["erro", "sistema"],
            ),
            TicketClassificationResult(
                category=TicketCategory.BILLING,
                priority=TicketPriority.MEDIUM,
                summary=("Foi identificado um problema relacionado à cobrança."),
                suggested_tags=["cobranca", "pagamento"],
            ),
        ],
    )

    evaluator = TicketEvaluatorService(
        classifier=classifier,
        strategy="one_shot",
    )

    report = asyncio.run(
        evaluator.evaluate(cases),
    )

    assert report.model == "test-model"
    assert report.strategy == "one_shot"

    assert report.total_cases == 2

    assert report.category_correct_count == 2
    assert report.priority_correct_count == 1
    assert report.joint_correct_count == 1

    assert report.category_accuracy == 1.0
    assert report.priority_accuracy == 0.5
    assert report.joint_accuracy == 0.5

    assert report.results[0].category_correct is True
    assert report.results[0].priority_correct is False
    assert report.results[0].joint_correct is False
    assert report.results[0].case_id == "case-1"
    assert report.results[0].expected_category is TicketCategory.TECHNICAL_ERROR
    assert report.results[0].predicted_category is TicketCategory.TECHNICAL_ERROR
    assert report.results[0].expected_priority is TicketPriority.HIGH
    assert report.results[0].predicted_priority is TicketPriority.MEDIUM

    assert report.results[1].category_correct is True
    assert report.results[1].priority_correct is True
    assert report.results[1].joint_correct is True
    assert report.results[1].case_id == "case-2"
    assert report.results[1].expected_category is TicketCategory.BILLING
    assert report.results[1].predicted_category is TicketCategory.BILLING
    assert report.results[1].expected_priority is TicketPriority.MEDIUM
    assert report.results[1].predicted_priority is TicketPriority.MEDIUM


def test_ticket_evaluator_rejects_empty_case_list() -> None:
    classifier = FakeTicketClassifier(predictions=[])

    evaluator = TicketEvaluatorService(
        classifier=classifier,
        strategy="one_shot",
    )

    with pytest.raises(
        ValueError,
        match="ao menos um caso",
    ):
        asyncio.run(
            evaluator.evaluate([]),
        )
