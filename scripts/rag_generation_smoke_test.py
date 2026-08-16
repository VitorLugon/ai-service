import asyncio

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.rag.prompt_builder import RagPromptBuilder
from app.schemas.rag import RagContext, RagSource
from app.schemas.tickets import TicketCategory
from app.services.rag_generation import RagGenerationService


async def main() -> None:
    """Executa um smoke test real e isolado da geração RAG."""

    settings = get_settings()

    if settings.openai_api_key is None:
        raise RuntimeError(
            "OPENAI_API_KEY não está configurada.",
        )

    question = "Como redefino minha senha?"
    context = RagContext(
        text=(
            "[SOURCE 1]\n"
            "id: recover-account-access\n"
            "title: Recuperar acesso à conta\n"
            "category: acesso_e_autenticacao\n"
            "content:\n"
            'Para redefinir a senha, utilize a opção "Esqueci minha senha" '
            "na tela de login."
        ),
        sources=[
            RagSource(
                article_id="recover-account-access",
                title="Recuperar acesso à conta",
                category=TicketCategory.ACCESS_AND_AUTHENTICATION,
                score=0.91,
                rank=1,
                content=(
                    'Para redefinir a senha, utilize a opção "Esqueci minha senha" '
                    "na tela de login."
                ),
            ),
        ],
        source_count=1,
    )
    prompt = RagPromptBuilder(
        question_max_characters=settings.rag_question_max_characters,
    ).build(
        question=question,
        context=context,
    )
    client = AsyncOpenAI(
        api_key=settings.openai_api_key.get_secret_value(),
    )
    service = RagGenerationService(
        client=client,
        model=settings.openai_rag_model,
        max_output_tokens=settings.rag_max_output_tokens,
    )

    try:
        result = await service.generate(
            prompt,
        )
    finally:
        await client.close()

    print(f"Modelo: {result.model}")
    print(f"Pergunta: {question}")
    print(f"Resposta: {result.answer}")
    print("Status: sucesso")


if __name__ == "__main__":
    asyncio.run(
        main(),
    )
