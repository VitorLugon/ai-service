import asyncio

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.core.vector_math import cosine_similarity

TEXTS = [
    "Não consigo acessar minha conta depois de redefinir a senha.",
    "Esqueci minha senha e preciso recuperar o acesso ao sistema.",
    "Gostaria de mudar o plano básico para o plano empresarial.",
]


async def main() -> None:
    """Executa uma comparação simples entre embeddings sintéticos."""

    settings = get_settings()

    if settings.openai_api_key is None:
        raise RuntimeError(
            "OPENAI_API_KEY não foi configurada.",
        )

    api_key = settings.openai_api_key.get_secret_value().strip()

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY está vazia.",
        )

    async with AsyncOpenAI(
        api_key=api_key,
        timeout=30.0,
        max_retries=2,
    ) as client:
        response = await client.embeddings.create(
            model=settings.openai_embedding_model,
            input=TEXTS,
            encoding_format="float",
        )

    ordered_embeddings = [
        item.embedding
        for item in sorted(
            response.data,
            key=lambda item: item.index,
        )
    ]

    if len(ordered_embeddings) != len(TEXTS):
        raise RuntimeError(
            "A resposta de embeddings não contém todos os textos enviados.",
        )

    dimensions = len(ordered_embeddings[0])
    password_similarity = cosine_similarity(
        ordered_embeddings[0],
        ordered_embeddings[1],
    )
    plan_similarity = cosine_similarity(
        ordered_embeddings[0],
        ordered_embeddings[2],
    )

    is_coherent = password_similarity > plan_similarity

    print(f"Modelo: {response.model}")
    print(f"Dimensões: {dimensions}")
    print(f"Similaridade senha: {password_similarity:.4f}")
    print(f"Similaridade plano: {plan_similarity:.4f}")
    print(
        "Interpretação: "
        + (
            "o texto de acesso ficou mais próximo do texto de senha."
            if is_coherent
            else "a ordenação semântica não ficou como esperado."
        ),
    )


if __name__ == "__main__":
    asyncio.run(main())
