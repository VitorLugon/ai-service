# ADR 0005 — Usar OpenAI Responses API para geração RAG

## Status

Aceita.

## Contexto

O pipeline precisa gerar respostas fundamentadas depois da recuperação, da
montagem de contexto e da montagem explícita do prompt.

## Decisão

Utilizar OpenAI Responses API por trás de `RagGenerationService`.

O serviço recebe apenas `RagPrompt`, envia `system_instructions` como
`instructions`, envia `user_message` como `input`, limita a saída por
`max_output_tokens` e valida `output_text`.

## Limites

`RagGenerationService` não conhece:

- Chroma;
- retrieval;
- FastAPI;
- sources.

Ele também não registra tools, não usa memória de conversa e não persiste
respostas.

## Consequências positivas

- provider isolado;
- testes com fake;
- Responses API centralizada;
- possibilidade futura de trocar modelo ou provider;
- separação entre prompt assembly e model invocation.

## Consequências negativas

- dependência externa;
- custo por chamada;
- latência;
- erros de provider;
- necessidade de avaliação de grounding.

## Fora do escopo

- streaming;
- tools;
- web search;
- file search;
- conversation memory;
- citations;
- endpoint HTTP.
