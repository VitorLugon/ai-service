# Semana 5 — Progresso

## Objetivo

Construir um pipeline RAG mantendo Retrieval, Augmentation e Generation
desacoplados.

## Dia 1

- schemas RAG;
- `RagContextBuilder`;
- orçamento de contexto;
- sources;
- truncamento controlado;
- ADR do pipeline.

## Dia 2

- schema de chunk;
- chunking determinístico;
- overlap;
- preservação de origem;
- integração do Context Builder com chunks;
- orçamento;
- testes;
- ADR de chunking.

## Pendências

- decidir reindexação por chunks;
- retrieval prompt;
- `GenerationService`;
- fontes/citações;
- comportamento sem evidência;
- avaliação RAG;
- integração HTTP.

## Checklist Manual DataCamp

Curso: Retrieval Augmented Generation (RAG) with LangChain

Capítulo 1 — Building RAG Applications with LangChain:

- Loading Documents for RAG with LangChain;
- Loading PDF files for RAG;
- Loading HTML files for RAG.
- Splitting documents for RAG;
- Exploring text splitting;
- Embedding and storing chunks;
- Creating a retriever / retrieval preparation.
