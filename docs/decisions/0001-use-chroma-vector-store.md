# ADR 0001 — Usar Chroma como armazenamento vetorial

## Status

Implementada.

## Contexto

O índice atual da base de conhecimento é linear e mantido em memória. Os
embeddings dos artigos podem ser reconstruídos na criação do serviço, o que é
adequado para o protótipo, mas aumenta custo e latência conforme a base cresce.

A evolução da busca semântica precisa permitir persistência, reutilização do
índice entre execuções e armazenamento conjunto de documentos e metadados. Em
etapas futuras, filtros por metadados também serão necessários para limitar a
busca por categoria, versão ou outras propriedades dos artigos.

## Decisão

A implementação persistente utiliza Chroma local e persistente.
`EmbeddingService` continua responsável por gerar embeddings, e a aplicação
fornece ao Chroma os vetores já calculados. A busca utiliza distância de
cosseno.

Configuração:

- coleção: `helpdesklite-knowledge-v1`;
- diretório local: `data/chroma`;
- ID do Chroma: ID do artigo;
- documento: conteúdo original do artigo;
- metadados: título, categoria, palavras-chave e versão;
- `embedding_model` como metadado quando aplicável.

Mapeamento:

```text
Chroma ID
└── KnowledgeArticle.id

Embedding
└── vetor do texto enriquecido

Document
└── conteúdo original do artigo

Metadata
├── title
├── category
├── keywords_json
├── schema_version
└── embedding_model, quando aplicável
```

Esta decisão foi implementada na Semana 4. O endpoint
`POST /internal/knowledge/search` consulta o backend Chroma carregado no
lifespan da aplicação, e `POST /internal/knowledge/search/batch` executa buscas
em lote. Filtros por categoria são convertidos internamente para `where`, sem
expor a sintaxe nativa do Chroma aos clientes HTTP.

`KnowledgeVectorIndex` foi preservado como implementação de referência em
memória para testes, avaliação e fallback explícito de desenvolvimento.

## Consequências positivas

- embeddings reutilizáveis;
- redução de chamadas repetidas;
- persistência local;
- suporte a filtros por categoria;
- suporte a consultas em lote;
- separação entre geração e armazenamento;
- possibilidade de trocar o adaptador futuramente.

## Consequências negativas

- nova dependência;
- arquivos persistentes;
- necessidade de sincronização;
- ciclo de vida da coleção;
- versionamento de coleção;
- migração quando modelo ou representação mudarem;
- maior complexidade de testes.

## Alternativas consideradas

### Manter somente o índice em memória

Adequado para o protótipo e para a base atual, mas sem persistência ou
reutilização dos embeddings entre execuções.

### Serviço vetorial gerenciado

Adiado porque a base atual é pequena e não justifica infraestrutura externa.

### Permitir que o Chroma gere embeddings

Rejeitado para preservar:

- `EmbeddingService`;
- tratamento de erros;
- configuração centralizada;
- testes determinísticos;
- independência do armazenamento.

## Limites

Ainda não serão implementados:

- Chroma Cloud;
- ambiente distribuído;
- busca híbrida;
- pipeline RAG;
- autenticação do banco;
- migração automática de coleções;
- filtros arbitrários por metadados;
- filtros compostos expostos via HTTP.
