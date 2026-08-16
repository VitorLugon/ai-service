# ADR 0004 — Usar contrato explícito para prompts RAG

## Status

Aceita.

## Contexto

O pipeline já separa retrieval e context assembly. A próxima etapa precisa
fornecer contexto ao modelo sem misturar:

- instruções;
- evidências;
- pergunta.

## Decisão

Representar o prompt com:

```text
RagPrompt
├── system_instructions
└── user_message
```

A user message contém seções explícitas:

```text
CONTEXTO
PERGUNTA
```

## Regras

- system instructions são estáveis;
- contexto é tratado como dado;
- pergunta não é colocada no system;
- contexto recuperado não é colocado no system;
- scores não são enviados;
- contexto vazio é explicitado;
- pergunta acima do limite é rejeitada.

## Consequências positivas

- testabilidade;
- separação de responsabilidades;
- segurança estrutural;
- provider independente;
- observabilidade futura;
- avaliação do prompt.

## Consequências negativas

- mais um tipo;
- mais um builder;
- prompt ainda precisa de defesas adicionais;
- delimitadores textuais não eliminam prompt injection.

## Fora do escopo

- OpenAI;
- geração;
- citations;
- streaming;
- endpoint;
- LangChain;
- guardrails avançados.
