from app.rag.chunker import RagTextChunker
from app.schemas.knowledge import KnowledgeArticle
from app.schemas.tickets import TicketCategory

CHUNK_SIZE = 2_000
OVERLAP = 200
PREVIEW_SIZE = 160


def main() -> None:
    """Inspeciona chunking RAG com artigo sintético."""

    article = KnowledgeArticle(
        id="synthetic-rag-runbook",
        title="Runbook sintético para suporte RAG",
        content=_build_long_content(),
        category=TicketCategory.TECHNICAL_ERROR,
        keywords=[
            "rag",
            "runbook",
        ],
    )
    chunker = RagTextChunker(
        chunk_size=CHUNK_SIZE,
        overlap=OVERLAP,
    )
    chunks = chunker.chunk_article(
        article,
    )

    print(f"Article: {article.id}")
    print(f"Characters: {len(article.content)}")
    print(f"Chunk size: {CHUNK_SIZE}")
    print(f"Overlap: {OVERLAP}")
    print(f"Chunks: {len(chunks)}")
    print("")

    for chunk in chunks:
        preview = chunk.content[:PREVIEW_SIZE].replace(
            "\n",
            " ",
        )
        print(f"Chunk {chunk.chunk_index}")
        print(f"ID: {chunk.chunk_id}")
        print(f"Characters: {len(chunk.content)}")
        print(f"Preview: {preview}")
        print("")


def _build_long_content() -> str:
    introduction = (
        "Este runbook sintético descreve um fluxo de investigação para falhas "
        "intermitentes em uma aplicação interna. "
    ) * 5
    steps = "\n".join(
        f"{index}. Validar a evidência operacional da etapa {index} antes de "
        "prosseguir para a próxima verificação."
        for index in range(
            1,
            22,
        )
    )
    final_notes = (
        "Observações finais: preservar fontes, registrar decisões e evitar "
        "alterações sem evidência suficiente. "
    ) * 5

    return f"{introduction}\n\n{steps}\n\n{final_notes}"


if __name__ == "__main__":
    main()
