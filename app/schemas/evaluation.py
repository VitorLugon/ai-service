from pydantic import BaseModel, ConfigDict, Field

from app.schemas.tickets import (
    TicketCategory,
    TicketClassificationInput,
    TicketPriority,
)


class TicketEvaluationCase(BaseModel):
    """Representa um chamado com sua classificação esperada."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(
        min_length=1,
        max_length=80,
    )
    ticket: TicketClassificationInput
    expected_category: TicketCategory
    expected_priority: TicketPriority
    rationale: str = Field(
        min_length=10,
        max_length=500,
    )


class TicketEvaluationItemResult(BaseModel):
    """Representa o resultado de um caso individual."""

    case_id: str
    expected_category: TicketCategory
    predicted_category: TicketCategory
    expected_priority: TicketPriority
    predicted_priority: TicketPriority
    category_correct: bool
    priority_correct: bool
    joint_correct: bool


class TicketEvaluationReport(BaseModel):
    """Representa as métricas de uma execução de avaliação."""

    model: str
    strategy: str
    total_cases: int = Field(ge=1)
    category_correct_count: int = Field(ge=0)
    priority_correct_count: int = Field(ge=0)
    joint_correct_count: int = Field(ge=0)
    category_accuracy: float = Field(ge=0, le=1)
    priority_accuracy: float = Field(ge=0, le=1)
    joint_accuracy: float = Field(ge=0, le=1)
    results: list[TicketEvaluationItemResult]
