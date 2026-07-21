import json
from typing import Any

import openai
from openai import AsyncOpenAI

from app.core.exceptions import (
    AIProviderConfigurationError,
    AIProviderConnectionError,
    AIProviderIncompleteResponseError,
    AIProviderInvalidResponseError,
    AIProviderRateLimitError,
    AIProviderRefusalError,
    AIProviderRequestError,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
)
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

        try:
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
        except openai.APITimeoutError as exc:
            raise AIProviderTimeoutError from exc
        except openai.RateLimitError as exc:
            raise AIProviderRateLimitError from exc
        except (
            openai.AuthenticationError,
            openai.PermissionDeniedError,
            openai.NotFoundError,
        ) as exc:
            raise AIProviderConfigurationError from exc
        except openai.APIConnectionError as exc:
            raise AIProviderConnectionError from exc
        except openai.InternalServerError as exc:
            raise AIProviderUnavailableError from exc
        except openai.APIStatusError as exc:
            raise AIProviderRequestError from exc
        except openai.APIError as exc:
            raise AIProviderRequestError from exc

        if response.status == "incomplete":
            raise AIProviderIncompleteResponseError

        if response.status != "completed":
            raise AIProviderInvalidResponseError

        if self._contains_refusal(response):
            raise AIProviderRefusalError

        parsed_output = response.output_parsed

        if not isinstance(
            parsed_output,
            TicketClassificationResult,
        ):
            raise AIProviderInvalidResponseError

        return parsed_output

    @staticmethod
    def _contains_refusal(response: Any) -> bool:
        """Verifica se a resposta contém uma recusa do modelo."""

        output_items = getattr(response, "output", [])

        for output_item in output_items:
            content_items = getattr(output_item, "content", [])

            for content_item in content_items:
                if getattr(content_item, "type", None) == "refusal":
                    return True

        return False

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
