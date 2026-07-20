import asyncio

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.prompts.ticket_classification import PromptStrategy
from app.schemas.tickets import TicketClassificationInput
from app.services.ticket_classifier import TicketClassifierService


async def main() -> None:
    """Compara as estratégias de prompt usando o mesmo chamado."""

    settings = get_settings()

    if settings.openai_api_key is None:
        raise RuntimeError(
            "OPENAI_API_KEY não foi configurada no arquivo .env.",
        )

    api_key = settings.openai_api_key.get_secret_value().strip()

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY está vazia no arquivo .env.",
        )

    ticket = TicketClassificationInput(
        title="Relatório exportado sem dados",
        description=(
            "A equipe financeira consegue visualizar o relatório na tela, "
            "mas o PDF exportado fica completamente em branco. "
            "O fechamento financeiro é amanhã e existe uma alternativa "
            "manual para obter os valores."
        ),
    )

    async with AsyncOpenAI(
        api_key=api_key,
        timeout=30.0,
        max_retries=2,
    ) as client:
        for strategy in PromptStrategy:
            classifier = TicketClassifierService(
                client=client,
                model=settings.openai_model,
                prompt_strategy=strategy,
            )

            result = await classifier.classify(ticket)

            print("=" * 60)
            print(f"Estratégia: {strategy.value}")
            print(f"Modelo: {result.model}")
            print("")
            print(result.model_dump_json(indent=2))
            print("")


if __name__ == "__main__":
    asyncio.run(main())
