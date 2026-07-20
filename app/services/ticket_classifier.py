import json

from openai import AsyncOpenAI

from app.prompts.ticket_classification import (
    PromptStrategy,
    build_ticket_classification_instructions,
)
from app.schemas.tickets import (
    TicketClassificationDraft,
    TicketClassificationInput,
)


class TicketClassifierService:
    """Classifica chamados de suporte usando um modelo de linguagem."""

    def __init__(
        self,
        client: AsyncOpenAI,
        model: str,
        prompt_strategy: PromptStrategy = PromptStrategy.FEW_SHOT,
    ) -> None:
        self._client = client
        self._model = model
        self._prompt_strategy = prompt_strategy

    async def classify(
        self,
        ticket: TicketClassificationInput,
    ) -> TicketClassificationDraft:
        """Classifica um chamado e retorna a resposta textual do modelo."""

        response = await self._client.responses.create(
            model=self._model,
            instructions=build_ticket_classification_instructions(
                self._prompt_strategy,
            ),
            input=self._serialize_ticket(ticket),
            max_output_tokens=500,
            store=False,
        )

        raw_output = response.output_text.strip()

        if not raw_output:
            raise RuntimeError(
                "O modelo retornou uma classificação vazia.",
            )

        return TicketClassificationDraft(
            model=self._model,
            raw_output=raw_output,
        )

    @staticmethod
    def _serialize_ticket(
        ticket: TicketClassificationInput,
    ) -> str:
        """Serializa o chamado para envio ao modelo."""

        return json.dumps(
            {
                "title": ticket.title,
                "description": ticket.description,
            },
            ensure_ascii=False,
        )
