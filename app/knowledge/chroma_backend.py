import json
from collections.abc import Mapping, Sequence
from math import isfinite
from typing import Protocol

from pydantic import ValidationError

from app.schemas.knowledge import KnowledgeArticle, KnowledgeSearchMatch
from app.schemas.tickets import TicketCategory

FLOAT_TOLERANCE = 1e-9


class ChromaKnowledgeError(RuntimeError):
    """Erro base da integração de leitura com Chroma."""


class ChromaKnowledgeInvalidRecordError(ChromaKnowledgeError):
    """Indica que o Chroma retornou um registro inválido."""


class ChromaKnowledgeCollection(Protocol):
    """Contrato mínimo de leitura da coleção Chroma."""

    def count(self) -> int:
        """Retorna a quantidade de registros."""

    def query(
        self,
        *,
        query_embeddings: Sequence[Sequence[float]],
        n_results: int,
        include: Sequence[str],
    ) -> Mapping[str, object]:
        """Consulta a coleção por embeddings explícitos."""


class ChromaKnowledgeSearchBackend:
    """Backend de busca semântica baseado em uma coleção Chroma."""

    def __init__(
        self,
        collection: ChromaKnowledgeCollection,
    ) -> None:
        self._collection = collection

    @property
    def size(self) -> int:
        """Retorna a quantidade de registros persistidos."""

        count = self._collection.count()

        if (
            not isinstance(
                count,
                int,
            )
            or count < 0
        ):
            raise ChromaKnowledgeInvalidRecordError(
                "A contagem da coleção Chroma é inválida.",
            )

        return count

    def search(
        self,
        query_embedding: Sequence[float],
        *,
        top_k: int = 3,
    ) -> list[KnowledgeSearchMatch]:
        """Busca artigos persistidos por similaridade de cosseno."""

        normalized_query_embedding = _normalize_embedding(
            query_embedding,
        )

        if top_k < 1:
            raise ValueError(
                "top_k deve ser maior que zero.",
            )

        collection_size = self.size

        if collection_size == 0:
            return []

        query_result = self._collection.query(
            query_embeddings=[
                list(normalized_query_embedding),
            ],
            n_results=min(
                top_k,
                collection_size,
            ),
            include=[
                "documents",
                "metadatas",
                "distances",
            ],
        )

        return _matches_from_query_result(
            query_result,
        )


def cosine_distance_to_similarity(
    distance: float,
) -> float:
    """Converte distância de cosseno do Chroma em similaridade."""

    normalized_distance = float(
        distance,
    )

    if not isfinite(
        normalized_distance,
    ):
        raise ValueError(
            "A distância de cosseno deve ser finita.",
        )

    score = 1.0 - normalized_distance

    if score < -1.0:
        if score >= -1.0 - FLOAT_TOLERANCE:
            return -1.0

        raise ValueError(
            "A distância de cosseno está fora do intervalo esperado.",
        )

    if score > 1.0:
        if score <= 1.0 + FLOAT_TOLERANCE:
            return 1.0

        raise ValueError(
            "A distância de cosseno está fora do intervalo esperado.",
        )

    return score


def knowledge_article_from_chroma_record(
    *,
    article_id: object,
    document: object,
    metadata: object,
) -> KnowledgeArticle:
    """Reconstrói um artigo a partir de um registro persistido no Chroma."""

    if (
        not isinstance(
            article_id,
            str,
        )
        or not article_id.strip()
    ):
        raise ChromaKnowledgeInvalidRecordError(
            "O registro do Chroma possui ID inválido.",
        )

    if (
        not isinstance(
            document,
            str,
        )
        or not document.strip()
    ):
        raise ChromaKnowledgeInvalidRecordError(
            "O registro do Chroma possui documento inválido.",
        )

    if not isinstance(
        metadata,
        Mapping,
    ):
        raise ChromaKnowledgeInvalidRecordError(
            "O registro do Chroma não possui metadata válida.",
        )

    title = _metadata_string(
        metadata,
        "title",
    )
    category = _metadata_string(
        metadata,
        "category",
    )
    keywords_json = _metadata_string(
        metadata,
        "keywords_json",
    )
    _metadata_int(
        metadata,
        "schema_version",
    )
    _metadata_string(
        metadata,
        "embedding_model",
    )
    keywords = _decode_keywords(
        keywords_json,
    )
    ticket_category = _decode_category(
        category,
    )

    try:
        return KnowledgeArticle(
            id=article_id,
            title=title,
            content=document,
            category=ticket_category,
            keywords=keywords,
        )
    except ValidationError as error:
        raise ChromaKnowledgeInvalidRecordError(
            "O registro do Chroma não corresponde a um artigo válido.",
        ) from error


def _normalize_embedding(
    embedding: Sequence[float],
) -> tuple[float, ...]:
    normalized_embedding = tuple(float(value) for value in embedding)

    if not normalized_embedding:
        raise ValueError(
            "O embedding da consulta não pode estar vazio.",
        )

    if any(not isfinite(value) for value in normalized_embedding):
        raise ValueError(
            "O embedding da consulta deve conter apenas valores finitos.",
        )

    return normalized_embedding


def _matches_from_query_result(
    query_result: Mapping[str, object],
) -> list[KnowledgeSearchMatch]:
    ids = _single_result_list(
        query_result,
        "ids",
    )
    documents = _single_result_list(
        query_result,
        "documents",
    )
    metadatas = _single_result_list(
        query_result,
        "metadatas",
    )
    distances = _single_result_list(
        query_result,
        "distances",
    )

    result_length = len(ids)

    if (
        len(documents) != result_length
        or len(metadatas) != result_length
        or len(distances) != result_length
    ):
        raise ChromaKnowledgeInvalidRecordError(
            "O Chroma retornou quantidades inconsistentes de resultados.",
        )

    matches: list[KnowledgeSearchMatch] = []

    for index in range(result_length):
        article = knowledge_article_from_chroma_record(
            article_id=ids[index],
            document=documents[index],
            metadata=metadatas[index],
        )
        distance = distances[index]

        if not isinstance(
            distance,
            int | float,
        ):
            raise ChromaKnowledgeInvalidRecordError(
                "O Chroma retornou distância inválida.",
            )

        matches.append(
            KnowledgeSearchMatch(
                article=article,
                score=cosine_distance_to_similarity(
                    float(distance),
                ),
            ),
        )

    return matches


def _single_result_list(
    query_result: Mapping[str, object],
    field_name: str,
) -> list[object]:
    value = query_result.get(
        field_name,
    )

    if not isinstance(
        value,
        list,
    ):
        raise ChromaKnowledgeInvalidRecordError(
            f"O Chroma não retornou o campo '{field_name}'.",
        )

    if len(value) != 1:
        raise ChromaKnowledgeInvalidRecordError(
            "O backend aceita exatamente uma consulta por vez.",
        )

    inner_value = value[0]

    if not isinstance(
        inner_value,
        list,
    ):
        raise ChromaKnowledgeInvalidRecordError(
            f"O campo '{field_name}' retornado pelo Chroma é inválido.",
        )

    return inner_value


def _metadata_string(
    metadata: Mapping[object, object],
    field_name: str,
) -> str:
    value = metadata.get(
        field_name,
    )

    if (
        not isinstance(
            value,
            str,
        )
        or not value.strip()
    ):
        raise ChromaKnowledgeInvalidRecordError(
            f"O registro do Chroma possui metadata inválida para '{field_name}'.",
        )

    return value


def _metadata_int(
    metadata: Mapping[object, object],
    field_name: str,
) -> int:
    value = metadata.get(
        field_name,
    )

    if not isinstance(
        value,
        int,
    ):
        raise ChromaKnowledgeInvalidRecordError(
            f"O registro do Chroma possui metadata inválida para '{field_name}'.",
        )

    return value


def _decode_keywords(
    keywords_json: str,
) -> list[str]:
    try:
        keywords = json.loads(
            keywords_json,
        )
    except json.JSONDecodeError as error:
        raise ChromaKnowledgeInvalidRecordError(
            "O registro do Chroma possui keywords_json inválido.",
        ) from error

    if not isinstance(
        keywords,
        list,
    ) or any(not isinstance(keyword, str) for keyword in keywords):
        raise ChromaKnowledgeInvalidRecordError(
            "O registro do Chroma possui keywords_json inválido.",
        )

    return keywords


def _decode_category(
    category: str,
) -> TicketCategory:
    try:
        return TicketCategory(
            category,
        )
    except ValueError as error:
        raise ChromaKnowledgeInvalidRecordError(
            "O registro do Chroma possui categoria inválida.",
        ) from error
