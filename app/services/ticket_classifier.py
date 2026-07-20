import json

from openai import AsyncOpenAI

from app.prompts.ticket_classification import (
    PromptStrategy,
    build_ticket_classification_instructions,
)
from app.schemas.tickets import (
    TicketClassificationInput,
    TicketClassificationResult,
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

    @property
    def model(self) -> str:
        """Retorna o modelo utilizado pelo classificador."""

        return self._model

    async def classify(
        self,
        ticket: TicketClassificationInput,
    ) -> TicketClassificationResult:
        """Classifica um chamado e retorna um objeto validado."""

        response = await self._client.responses.parse(
            model=self._model,
            instructions=build_ticket_classification_instructions(
                self._prompt_strategy,
            ),
            input=self._serialize_ticket(ticket),
            text_format=TicketClassificationResult,
            max_output_tokens=500,
            store=False,
        )

        parsed_output = response.output_parsed

        if not isinstance(
            parsed_output,
            TicketClassificationResult,
        ):
            raise RuntimeError(
                "O modelo não retornou uma classificação estruturada.",
            )

        return parsed_output

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
