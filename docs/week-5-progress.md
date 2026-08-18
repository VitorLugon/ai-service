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

## Dia 4

- `RagGenerationResult`;
- `RagGenerationService`;
- Responses API;
- tradução de erros;
- geração fundamentada;
- cenário sem evidência;
- smoke test isolado;
- teste integrado Context -> Prompt -> Generation.

## Dia 5

- `RagAnswerSource`;
- `RagAnswer`;
- `RagAnswerComposer`;
- source attribution controlada pela aplicação;
- source IDs determinísticos por artigo ou chunk;
- deduplicação por `source_id`;
- suporte a artigo inteiro e chunk;
- comportamento explícito sem evidência;
- teste de source hallucination;
- teste de fonte removida pelo orçamento;
- pipeline Context -> Prompt -> Generation -> Answer.

## Dia 6

- dataset de avaliação RAG;
- schemas de evaluation;
- `RagEvaluator`;
- retrieval hit;
- source hit;
- keyword coverage;
- refusal metrics;
- unsupported answer;
- avaliação offline;
- script real controlado;
- baseline documentado.

## Pendências

- decidir reindexação por chunks;
- integração RAG end-to-end;
- endpoint RAG;
- avaliação final;
- revisão de segurança;
- fechamento da Semana 5.
- métricas de groundedness;
- citation verification;
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
