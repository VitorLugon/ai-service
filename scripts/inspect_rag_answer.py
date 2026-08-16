from app.schemas.rag import (
    RagContext,
    RagGenerationResult,
    RagSource,
)
from app.schemas.tickets import TicketCategory
from app.services.rag_answer import RagAnswerComposer


def main() -> None:
    """Inspeciona uma resposta RAG fundamentada com dados sintéticos."""

    context = RagContext(
        text=(
            "[SOURCE 1]\n"
            "article_id: recover-account-access\n"
            "chunk_id: recover-account-access#chunk-000\n"
            "title: Recuperar acesso à conta\n"
            "category: acesso_e_autenticacao\n"
            "content:\n"
            "Para redefinir a senha, utilize a opção Esqueci minha senha."
        ),
        sources=[
            RagSource(
                article_id="recover-account-access",
                title="Recuperar acesso à conta",
                category=TicketCategory.ACCESS_AND_AUTHENTICATION,
                score=0.91,
                rank=1,
                content=(
                    "Para redefinir a senha, utilize a opção Esqueci minha senha."
                ),
                chunk_index=0,
                chunk_id="recover-account-access#chunk-000",
            ),
        ],
        source_count=1,
    )
    generation = RagGenerationResult(
        answer=(
            "Use a opção Esqueci minha senha na tela de login para redefinir sua senha."
        ),
        model="gpt-5-mini",
    )
    answer = RagAnswerComposer().compose(
        generation=generation,
        context=context,
    )

    print("ANSWER")
    print("======")
    print("")
    print(answer.answer)
    print("")
    print("SOURCES")
    print("=======")
    print("")

    for index, source in enumerate(
        answer.sources,
        start=1,
    ):
        print(f"{index}. {source.source_id}")
        print(f"   article: {source.article_id}")
        print(f"   chunk: {source.chunk_id or '-'}")
        print(f"   title: {source.title}")
        print(f"   category: {source.category.value}")


if __name__ == "__main__":
    main()
