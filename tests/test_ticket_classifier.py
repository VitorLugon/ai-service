import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from app.prompts.ticket_classification import PromptStrategy
from app.schemas.tickets import TicketClassificationInput
from app.services.ticket_classifier import TicketClassifierService


def test_ticket_classifier_returns_model_output() -> None:
    expected_output = (
        "Categoria: acesso_e_autenticacao\n"
        "Prioridade: alta\n"
        "Resumo: Usuário não consegue acessar a conta.\n"
        "Tags: login, senha"
    )

    client = MagicMock()
    client.responses.create = AsyncMock(
        return_value=SimpleNamespace(
            output_text=expected_output,
        ),
    )

    classifier = TicketClassifierService(
        client=client,
        model="test-model",
    )

    ticket = TicketClassificationInput(
        title="Erro ao entrar",
        description="Não consigo acessar minha conta com a nova senha.",
    )

    result = asyncio.run(classifier.classify(ticket))

    assert result.model == "test-model"
    assert result.raw_output == expected_output

    client.responses.create.assert_awaited_once()

    request = client.responses.create.await_args.kwargs

    assert request["model"] == "test-model"
    assert request["max_output_tokens"] == 500
    assert request["store"] is False
    assert '"title": "Erro ao entrar"' in request["input"]
    assert "Não consigo acessar minha conta" in request["input"]


def test_ticket_classifier_rejects_empty_model_output() -> None:
    client = MagicMock()
    client.responses.create = AsyncMock(
        return_value=SimpleNamespace(
            output_text="   ",
        ),
    )

    classifier = TicketClassifierService(
        client=client,
        model="test-model",
    )

    ticket = TicketClassificationInput(
        title="Erro ao entrar",
        description="Não consigo acessar minha conta com a nova senha.",
    )

    with pytest.raises(
        RuntimeError,
        match="classificação vazia",
    ):
        asyncio.run(classifier.classify(ticket))


def test_ticket_input_rejects_short_description() -> None:
    with pytest.raises(ValidationError):
        TicketClassificationInput(
            title="Erro ao entrar",
            description="Erro",
        )


def test_ticket_classifier_uses_selected_prompt_strategy() -> None:
    client = MagicMock()
    client.responses.create = AsyncMock(
        return_value=SimpleNamespace(
            output_text=(
                "Categoria: cobranca\n"
                "Prioridade: media\n"
                "Resumo: Cliente recebeu cobrança duplicada.\n"
                "Tags: pagamento, duplicidade"
            ),
        ),
    )

    classifier = TicketClassifierService(
        client=client,
        model="test-model",
        prompt_strategy=PromptStrategy.ONE_SHOT,
    )

    ticket = TicketClassificationInput(
        title="Cobrança duplicada",
        description="A mesma mensalidade foi cobrada duas vezes.",
    )

    asyncio.run(classifier.classify(ticket))

    request = client.responses.create.await_args.kwargs
    instructions = request["instructions"]

    assert instructions.count("<expected_output id=") == 1
