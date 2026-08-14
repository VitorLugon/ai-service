# ADR 0003 — Usar chunking determinístico antes da geração RAG

## Status

Aceita.

## Contexto

Artigos longos podem ultrapassar o orçamento de contexto e conter múltiplos
assuntos. Antes da futura geração RAG, a camada de Augmentation precisa
transformar documentos recuperados em unidades menores, rastreáveis e
previsíveis.

## Decisão

Usar estratégia própria e determinística de chunking com:

- tamanho configurável;
- overlap configurável;
- preferência por separadores naturais;
- IDs determinísticos;
- preservação da origem.

`KnowledgeArticle` continua representando o documento de origem. `RagChunk`
representa um trecho derivado desse documento e preserva `article_id`, título,
categoria, índice e conteúdo. O `chunk_id` é derivado de forma determinística no
formato `<article-id>#chunk-000`.

Neste momento, o Chroma real continua indexando artigos inteiros. A indexação
por chunk exigirá decisão posterior, nova versão de schema, possível nova
coleção, reindexação e nova avaliação de retrieval.

## Consequências Positivas

- testabilidade;
- rastreabilidade;
- independência de framework;
- controle de contexto;
- futura indexação por chunk.

## Consequências Negativas

- algoritmo mais simples que soluções especializadas;
- ausência de split semântico;
- caracteres em vez de tokens;
- necessidade futura de reindexação caso Chroma passe a usar chunks.

## Fora Do Escopo

- semantic chunking;
- token-aware splitting;
- LangChain splitters;
- LLM chunking;
- reindexação do Chroma neste dia.
