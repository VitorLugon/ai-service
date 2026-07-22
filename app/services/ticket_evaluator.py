from collections.abc import Sequence
from typing import Protocol

from app.schemas.evaluation import (
    TicketEvaluationCase,
    TicketEvaluationItemResult,
    TicketEvaluationReport,
)
from app.schemas.tickets import (
    TicketClassificationInput,
    TicketClassificationResult,
)


class TicketClassifierProtocol(Protocol):
    """Contrato mínimo necessário para avaliar um classificador."""

    @property
    def model(self) -> str:
        """Retorna o modelo utilizado."""

    async def classify(
        self,
        ticket: TicketClassificationInput,
    ) -> TicketClassificationResult:
        """Classifica um chamado."""


class TicketEvaluatorService:
    """Avalia um classificador usando resultados esperados."""

    def __init__(
        self,
        classifier: TicketClassifierProtocol,
        strategy: str,
    ) -> None:
        self._classifier = classifier
        self._strategy = strategy

    async def evaluate(
        self,
        cases: Sequence[TicketEvaluationCase],
    ) -> TicketEvaluationReport:
        """Executa os casos e calcula métricas de acurácia."""

        if not cases:
            raise ValueError(
                "É necessário informar ao menos um caso.",
            )

        results: list[TicketEvaluationItemResult] = []

        for case in cases:
            prediction = await self._classifier.classify(
                case.ticket,
            )

            category_correct = prediction.category == case.expected_category
            priority_correct = prediction.priority == case.expected_priority

            results.append(
                TicketEvaluationItemResult(
                    case_id=case.id,
                    expected_category=case.expected_category,
                    predicted_category=prediction.category,
                    expected_priority=case.expected_priority,
                    predicted_priority=prediction.priority,
                    category_correct=category_correct,
                    priority_correct=priority_correct,
                    joint_correct=(category_correct and priority_correct),
                ),
            )

        total_cases = len(results)

        category_correct_count = sum(result.category_correct for result in results)
        priority_correct_count = sum(result.priority_correct for result in results)
        joint_correct_count = sum(result.joint_correct for result in results)

        return TicketEvaluationReport(
            model=self._classifier.model,
            strategy=self._strategy,
            total_cases=total_cases,
            category_correct_count=category_correct_count,
            priority_correct_count=priority_correct_count,
            joint_correct_count=joint_correct_count,
            category_accuracy=(category_correct_count / total_cases),
            priority_accuracy=(priority_correct_count / total_cases),
            joint_accuracy=(joint_correct_count / total_cases),
            results=results,
        )
