# ADR 0006 — Manter atribuição de fontes RAG sob controle da aplicação

## Status

Aceita.

## Contexto

LLMs podem produzir IDs, marcadores e referências inexistentes. Em um fluxo RAG,
isso pode fazer uma resposta mencionar fontes que não foram recuperadas, não
foram enviadas ao modelo ou foram removidas pelo orçamento de contexto.

O projeto já separa recuperação, montagem de contexto, montagem de prompt e
geração. A etapa de geração retorna apenas texto em `RagGenerationResult`,
enquanto `RagContext` mantém as evidências selecionadas pela aplicação.

## Decisão

A aplicação determina `sources` usando exclusivamente `RagContext.sources`.

O modelo produz somente `answer`. A aplicação compõe `RagAnswer` combinando o
texto gerado com as fontes do contexto por meio de `RagAnswerComposer`.

`source_id` é determinístico:

- usa `chunk_id` quando a fonte vem de um chunk;
- usa `article_id` quando a fonte vem de um artigo inteiro.

O composer não parseia IDs citados pelo modelo, não interpreta marcadores como
`[SOURCE n]` e não adiciona fontes que não estejam no contexto.

## Consequência

O sistema pode garantir que nenhuma source retornada seja inventada pelo
modelo. Também pode garantir que uma fonte removida antes da geração não
reapareça no contrato final de resposta.

## Limitação

As sources representam contexto fornecido ao modelo. Elas ainda não provam que
cada claim da resposta foi sustentada por uma fonte específica.

O projeto ainda não possui verificação de citações por claim, checagem de
entailment ou avaliação automática de groundedness.

## Futuro

- citações por claim;
- verificação de citações;
- entailment checking;
- avaliação de groundedness;
- avaliação RAG end-to-end.
