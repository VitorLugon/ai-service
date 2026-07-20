import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from app.prompts.ticket_classification import PromptStrategy
from app.schemas.tickets import (
    TicketCategory,
    TicketClassificationInput,
    TicketClassificationResult,
    TicketPriority,
)
from app.services.ticket_classifier import TicketClassifierService


def create_ticket() -> TicketClassificationInput:
    """Cria um chamado válido para os testes."""

    return TicketClassificationInput(
        title="Erro ao entrar",
        description="Não consigo acessar minha conta com a nova senha.",
    )


def test_ticket_classifier_returns_structured_output() -> None:
    expected_result = TicketClassificationResult(
        category=TicketCategory.ACCESS_AND_AUTHENTICATION,
        priority=TicketPriority.HIGH,
        summary="Usuário não consegue acessar a conta com a nova senha.",
        suggested_tags=["login", "senha"],
    )

    client = MagicMock()
    client.responses.parse = AsyncMock(
        return_value=SimpleNamespace(
            output_parsed=expected_result,
        ),
    )

    classifier = TicketClassifierService(
        client=client,
        model="test-model",
    )

    result = asyncio.run(
        classifier.classify(create_ticket()),
    )

    assert result == expected_result
    assert classifier.model == "test-model"

    client.responses.parse.assert_awaited_once()

    request = client.responses.parse.await_args.kwargs

    assert request["model"] == "test-model"
    assert request["text_format"] is TicketClassificationResult
    assert request["max_output_tokens"] == 500
    assert request["store"] is False
    assert '"title": "Erro ao entrar"' in request["input"]


def test_ticket_classifier_rejects_missing_parsed_output() -> None:
    client = MagicMock()
    client.responses.parse = AsyncMock(
        return_value=SimpleNamespace(
            output_parsed=None,
        ),
    )

    classifier = TicketClassifierService(
        client=client,
        model="test-model",
    )

    with pytest.raises(
        RuntimeError,
        match="classificação estruturada",
    ):
        asyncio.run(
            classifier.classify(create_ticket()),
        )


def test_ticket_classifier_uses_selected_prompt_strategy() -> None:
    expected_result = TicketClassificationResult(
        category=TicketCategory.BILLING,
        priority=TicketPriority.MEDIUM,
        summary="Cliente recebeu uma cobrança duplicada na assinatura.",
        suggested_tags=["pagamento", "duplicidade"],
    )

    client = MagicMock()
    client.responses.parse = AsyncMock(
        return_value=SimpleNamespace(
            output_parsed=expected_result,
        ),
    )

    classifier = TicketClassifierService(
        client=client,
        model="test-model",
        prompt_strategy=PromptStrategy.ONE_SHOT,
    )

    asyncio.run(
        classifier.classify(create_ticket()),
    )

    request = client.responses.parse.await_args.kwargs
    instructions = request["instructions"]

    assert instructions.count("<expected_output id=") == 1


def test_ticket_input_rejects_short_description() -> None:
    with pytest.raises(ValidationError):
        TicketClassificationInput(
            title="Erro ao entrar",
            description="Erro",
        )


def test_classification_rejects_invalid_category() -> None:
    with pytest.raises(ValidationError):
        TicketClassificationResult(
            category="categoria_inexistente",
            priority=TicketPriority.LOW,
            summary="Não foi possível identificar o tipo do problema.",
            suggested_tags=["triagem"],
        )
