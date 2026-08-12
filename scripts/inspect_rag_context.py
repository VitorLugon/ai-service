from app.rag.context_builder import RagContextBuilder
from app.schemas.knowledge import KnowledgeArticle, KnowledgeSearchMatch
from app.schemas.tickets import TicketCategory


def main() -> None:
    """Inspeciona a montagem de contexto RAG com dados sintéticos."""

    articles = [
        KnowledgeArticle(
            id="recover-account-access",
            title="Recuperar acesso à conta",
            content=(
                "Oriente o usuário a abrir a tela de login, selecionar recuperação "
                "de acesso e confirmar o e-mail cadastrado antes de solicitar nova "
                "senha temporária ao suporte interno."
            ),
            category=TicketCategory.ACCESS_AND_AUTHENTICATION,
            keywords=[
                "acesso",
                "senha",
            ],
        ),
        KnowledgeArticle(
            id="billing-invoice-copy",
            title="Emitir segunda via de fatura",
            content=(
                "A segunda via da fatura fica disponível no menu de cobrança. "
                "Confira o período, gere o PDF e valide se o status do pagamento "
                "foi atualizado após a compensação."
            ),
            category=TicketCategory.BILLING,
            keywords=[
                "fatura",
                "cobranca",
            ],
        ),
    ]
    matches = [
        KnowledgeSearchMatch(
            article=articles[0],
            score=0.91,
        ),
        KnowledgeSearchMatch(
            article=articles[1],
            score=0.72,
        ),
    ]

    context = RagContextBuilder(
        max_characters=1_000,
    ).build(
        matches,
    )

    print(f"source_count: {context.source_count}")
    print(f"characters: {len(context.text)}")
    print("source_ids: " + ", ".join(source.article_id for source in context.sources))
    print("")
    print(context.text)


if __name__ == "__main__":
    main()
