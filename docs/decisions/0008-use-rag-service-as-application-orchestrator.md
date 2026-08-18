# ADR 0008 — Usar RagService Como Orquestrador De Aplicação

## Status

Aceita.

## Contexto

Ao final da Semana 5, as etapas do pipeline RAG já existem separadamente:

- recuperação semântica;
- montagem de contexto;
- montagem de prompt;
- geração;
- composição de resposta com fontes.

Era necessário expor uma rota HTTP end-to-end sem mover regras de pipeline para
FastAPI e sem acoplar os serviços a `AsyncOpenAI`, Chroma concreto ou Settings.

## Decisão

Criar `RagService` em `app/services/rag_service.py` como orquestrador de
aplicação. O serviço recebe todos os componentes por injeção e executa:

```text
search
  |
  v
context
  |
  v
prompt
  |
  v
generation
  |
  v
answer composition
```

A rota `POST /internal/rag/answer` fica fina: valida o payload, aplica
autenticação interna, cria filtro de domínio quando necessário e delega para
`RagService`.

A dependência FastAPI é a única responsável pelo wiring com Settings,
`AsyncOpenAI`, `EmbeddingService`, `KnowledgeSearchService`,
`RagGenerationService` e backend Chroma inicializado no lifespan.

## Consequências Positivas

- o pipeline pode ser testado sem FastAPI;
- a rota pode ser testada com serviço falso;
- Chroma e OpenAI permanecem nas bordas;
- o evaluator continua fora do caminho de request;
- fica simples trocar retrieval, prompt builder ou generation service.

## Consequências Negativas

- existe uma camada a mais de wiring;
- os contratos entre etapas precisam permanecer bem documentados;
- testes precisam cobrir tanto unidade quanto integração HTTP.

## Fora Do Escopo

- streaming;
- reranking;
- LangChain;
- verificação automática de citações por claim;
- reindexação por chunks.
