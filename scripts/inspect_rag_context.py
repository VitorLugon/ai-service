from app.rag.chunker import RagTextChunker
from app.rag.context_builder import RagContextBuilder
from app.schemas.knowledge import KnowledgeArticle, KnowledgeSearchMatch
from app.schemas.rag import RankedRagChunk
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

    chunker = RagTextChunker(
        chunk_size=500,
        overlap=80,
    )
    chunks = chunker.chunk_article(
        KnowledgeArticle(
            id="technical-runbook",
            title="Investigar falha técnica",
            content=(
                "Primeiro parágrafo com contexto operacional da falha técnica. "
                "Ele descreve sintomas observáveis e sinais de impacto. "
                "Também registra como separar evidências de hipóteses. " * 4 + "\n\n"
                "Segundo parágrafo com etapas de verificação e coleta de logs. "
                "Ele deve permanecer rastreável até o artigo original. "
                "Cada etapa precisa ser validada antes da próxima ação. " * 4 + "\n\n"
                "Terceiro parágrafo com critérios de encerramento do diagnóstico. "
                "O suporte deve registrar a causa provável e os próximos passos."
            ),
            category=TicketCategory.TECHNICAL_ERROR,
            keywords=[
                "erro",
                "logs",
            ],
        ),
    )
    chunk_context = RagContextBuilder(
        max_characters=1_000,
    ).build_from_chunks(
        [
            RankedRagChunk(
                chunk=chunk,
                score=0.8 - (chunk.chunk_index * 0.1),
                rank=chunk.chunk_index + 1,
            )
            for chunk in chunks
        ],
    )

    print(f"source_count: {context.source_count}")
    print(f"characters: {len(context.text)}")
    print("source_ids: " + ", ".join(source.article_id for source in context.sources))
    print("")
    print(context.text)
    print("")
    print(f"chunks_available: {len(chunks)}")
    print(f"chunk_context_characters: {len(chunk_context.text)}")
    print(
        "chunk_source_ids: "
        + ", ".join(
            source.chunk_id or source.article_id for source in chunk_context.sources
        )
    )


if __name__ == "__main__":
    main()
