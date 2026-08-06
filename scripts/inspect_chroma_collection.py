from app.core.config import get_settings
from app.knowledge.chroma import (
    create_persistent_chroma_client,
    get_or_create_knowledge_collection,
)


def main() -> None:
    """Inspeciona a coleção Chroma persistente configurada."""

    settings = get_settings()
    client = create_persistent_chroma_client(
        settings.chroma_persist_directory,
    )
    collection = get_or_create_knowledge_collection(
        client,
        name=settings.chroma_collection_name,
        schema_version=settings.chroma_schema_version,
        embedding_model=settings.openai_embedding_model,
    )
    collection_names = _collection_names(
        client.list_collections(),
    )

    print(f"Diretório persistente: {settings.chroma_persist_directory}")
    print(f"Coleção: {collection.name}")
    print(f"Registros: {collection.count()}")
    print(f"Coleções disponíveis: {', '.join(collection_names)}")
    print("Coleção persistente validada com sucesso.")


def _collection_names(
    collections: object,
) -> list[str]:
    names: list[str] = []

    if not isinstance(
        collections,
        list | tuple,
    ):
        return names

    for collection in collections:
        if isinstance(
            collection,
            str,
        ):
            names.append(
                collection,
            )
            continue

        name = getattr(
            collection,
            "name",
            None,
        )

        if isinstance(
            name,
            str,
        ):
            names.append(
                name,
            )

    return names


if __name__ == "__main__":
    main()
