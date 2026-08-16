from app.rag.prompt_builder import RagPromptBuilder
from app.schemas.rag import RagContext, RagSource
from app.schemas.tickets import TicketCategory


def main() -> None:
    """Inspeciona o contrato de prompt RAG com dados sintéticos."""

    context = RagContext(
        text=(
            "[SOURCE 1]\n"
            "id: recover-account-access\n"
            "title: Recuperar acesso à conta\n"
            "category: acesso_e_autenticacao\n"
            "content:\n"
            "Oriente o usuário a confirmar o e-mail cadastrado e usar o fluxo "
            "de recuperação de acesso.\n\n"
            "[SOURCE 2]\n"
            "id: billing-invoice-copy\n"
            "title: Emitir segunda via de fatura\n"
            "category: cobranca\n"
            "content:\n"
            "A segunda via da fatura fica disponível no menu de cobrança."
        ),
        sources=[
            RagSource(
                article_id="recover-account-access",
                title="Recuperar acesso à conta",
                category=TicketCategory.ACCESS_AND_AUTHENTICATION,
                score=0.91,
                rank=1,
                content=(
                    "Oriente o usuário a confirmar o e-mail cadastrado e usar o "
                    "fluxo de recuperação de acesso."
                ),
            ),
            RagSource(
                article_id="billing-invoice-copy",
                title="Emitir segunda via de fatura",
                category=TicketCategory.BILLING,
                score=0.72,
                rank=2,
                content=(
                    "A segunda via da fatura fica disponível no menu de cobrança."
                ),
            ),
        ],
        source_count=2,
    )
    builder = RagPromptBuilder(
        question_max_characters=2_000,
    )
    prompt = builder.build(
        question="Como recuperar minha conta?",
        context=context,
    )
    empty_context_prompt = builder.build(
        question="Existe orientação para trocar o idioma da conta?",
        context=RagContext(
            text="",
            sources=[],
            source_count=0,
        ),
    )

    print("SYSTEM")
    print("======")
    print("")
    print(prompt.system_instructions)
    print("")
    print("USER")
    print("====")
    print("")
    print(prompt.user_message)
    print("")
    print("USER SEM CONTEXTO")
    print("================")
    print("")
    print(empty_context_prompt.user_message)


if __name__ == "__main__":
    main()
