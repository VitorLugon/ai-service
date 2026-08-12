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
Augmentation / RagContextBuilder
    |
    v
RagContext
    |
    v
Generation
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
- preservação da origem.

`RagContext.text` contém somente o texto que respeita o orçamento configurado.
`RagSource.content` preserva o conteúdo original completo do artigo, mesmo
quando o texto de contexto é truncado. Essa decisão facilita citações,
auditoria e debugging.

## Generation

Futura responsabilidade por:

- instruções;
- uso do contexto;
- resposta;
- fontes e citações;
- comportamento sem evidência.

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
