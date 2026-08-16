# ADR 0002 — Separar Retrieval, Augmentation e Generation

## Status

Aceita.

## Contexto

O projeto já possui retrieval persistente com Chroma, geração de embeddings
desacoplada, filtros por categoria, busca em lote e avaliação quantitativa da
recuperação. A próxima etapa é adicionar geração de respostas sem acoplar:

- vector store;
- preparação de contexto;
- modelo generativo.

## Decisão

O pipeline RAG será separado em três estágios:

```text
Retrieval
    |
    v
KnowledgeSearchMatch[]
    |
    v
Augmentation / Context Assembly
    |
    v
RagContext
    |
    v
Augmentation / Prompt Assembly
    |
    v
RagPrompt
    |
    v
RagGenerationService
    |
    v
OpenAI Responses API
    |
    v
RagGenerationResult
```

## Retrieval

Responsável por:

- embeddings da query;
- busca;
- filtros;
- ranking.

## Augmentation

Responsável por:

- seleção das fontes que cabem;
- preservação da ordem recebida;
- formatação textual;
- limite de contexto;
- preservação da origem;
- montagem do contrato de prompt.

`RagContext.text` contém somente o texto que respeita o orçamento configurado.
`RagSource.content` preserva o conteúdo original completo do artigo, mesmo
quando o texto de contexto é truncado. Essa decisão facilita citações,
auditoria e debugging.

Augmentation passa a conter duas etapas:

```text
Context Assembly
      |
      v
Prompt Assembly
```

O estado atual do pipeline é:

```text
Retrieval
   |
   v
KnowledgeSearchMatch[]
   |
   v
Chunking / Context Builder
   |
   v
RagContext
   |
   v
RagPromptBuilder
   |
   v
RagPrompt
   |
   v
RagGenerationService
   |
   v
OpenAI Responses API
   |
   v
RagGenerationResult
```

## Generation

Responsável por:

- receber `RagPrompt` como única entrada de conteúdo;
- chamar a OpenAI Responses API;
- validar resposta textual;
- traduzir erros do provider;
- retornar `RagGenerationResult`.

Ainda são responsabilidades futuras:

- fontes e citações formais;
- endpoint RAG;
- streaming;
- avaliação end-to-end.

## Consequências Positivas

- testes independentes;
- menor acoplamento;
- observabilidade;
- avaliação separada;
- troca de retriever;
- troca de modelo;
- citações futuras.

## Consequências Negativas

- mais tipos;
- mais serviços;
- mais wiring;
- necessidade de contratos claros.

## Fora Do Escopo

- LangChain;
- geração;
- streaming;
- endpoint RAG;
- defesa completa contra prompt injection;
- reranking.
