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

## Dia 3

- `RagPrompt`;
- `RagPromptBuilder`;
- system/user separados;
- contexto delimitado;
- pergunta delimitada;
- limite da pergunta;
- comportamento sem contexto;
- proteção estrutural contra prompt injection;
- contrato pronto para Generation.

## Pendências

- decidir reindexação por chunks;
- `GenerationService`;
- integração com OpenAI Responses API;
- resposta estruturada;
- fontes/citações;
- endpoint RAG;
- avaliação end-to-end;
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
- Retrieval prompt;
- Combining documents/context with the model;
- Retrieval chain.
