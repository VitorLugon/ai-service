# Revisão da Semana 4

## Objetivo

Migrar a recuperação semântica de um índice reconstruído em memória para um
armazenamento vetorial persistente com Chroma, preservando testes
determinísticos e a separação entre geração de embeddings, armazenamento e
busca.

## Evolução

### Antes

- embeddings dos artigos eram temporários;
- o índice era reconstruído em memória;
- a busca era linear com `KnowledgeVectorIndex`;
- cada fluxo real precisava gerar embeddings dos artigos novamente.

### Depois

- Chroma local persistente armazena embeddings, documentos e metadata;
- artigos são pré-indexados por script explícito;
- requests geram apenas embeddings das queries;
- o backend é carregado no lifespan da aplicação;
- filtros por categoria são convertidos para `where` internamente;
- buscas em lote usam `embed_texts` e uma chamada batch ao Chroma.

## Funcionalidades Entregues

- `PersistentClient` local;
- coleção `helpdesklite-knowledge-v1`;
- `embedding_function=None`;
- metadata versionada;
- indexação idempotente com `upsert`;
- backend Chroma para busca individual;
- conversão de distância de cosseno para similaridade;
- reconstrução de `KnowledgeArticle`;
- update/delete por ID em serviço interno;
- endpoint individual usando Chroma;
- filtros por categoria;
- endpoint batch;
- script de consulta individual;
- script de consulta batch;
- script de avaliação Chroma;
- testes de equivalência entre memória e Chroma.

## Arquitetura Final

Indexação:

```text
knowledge/articles.json
        |
        v
EmbeddingService
        |
        v
Chroma upsert
```

Busca:

```text
HTTP
        |
        v
EmbeddingService(query)
        |
        v
Chroma query
        |
        v
KnowledgeSearchMatch[]
```

Batch:

```text
queries[]
        |
        v
EmbeddingService.embed_texts
        |
        v
Chroma query batch
        |
        v
rankings[]
```

## Persistência

- diretório: `data/chroma`;
- coleção: `helpdesklite-knowledge-v1`;
- schema: `CHROMA_SCHEMA_VERSION`;
- modelo: `OPENAI_EMBEDDING_MODEL`;
- embeddings do Chroma: desabilitados com `embedding_function=None`.

## Avaliação

O baseline real em memória registrado em `docs/evaluation.md` usa
`text-embedding-3-small`, 12 artigos e 18 consultas sintéticas:

| Métrica | Memória | Chroma | Diferença |
|---|---:|---:|---:|
| Hit Rate@1 | 1,0000 | 1,0000 | 0,0000 |
| Hit Rate@3 | 1,0000 | 1,0000 | 0,0000 |
| Hit Rate@5 | 1,0000 | 1,0000 | 0,0000 |
| Recall@1 | 0,8333 | 0,8333 | 0,0000 |
| Recall@3 | 1,0000 | 1,0000 | 0,0000 |
| Recall@5 | 1,0000 | 1,0000 | 0,0000 |
| MRR | 1,0000 | 1,0000 | 0,0000 |

A avaliação real Chroma foi executada em 2026-08-10 com
`text-embedding-3-small`, 12 artigos indexados e 18 consultas sintéticas. O
resultado agregado ficou equivalente ao baseline em memória.

## Comparação Memória Vs Chroma

Os testes determinísticos com vetores sintéticos confirmam equivalência de:

- IDs recuperados;
- top-k;
- scores dentro de tolerância;
- reconstrução de artigos;
- métricas agregadas do evaluator;
- batch vs buscas individuais.

## Diferenças Observadas

`KnowledgeVectorIndex` usa desempate determinístico por ID. O Chroma não deve
ser tratado como fonte de desempate por ID em empates exatos; os testes validam
o conjunto de itens e os scores, sem impor a mesma ordem nesses casos.

## Testes

A suíte cobre:

- unitários de Chroma;
- integração Chroma em `tmp_path`;
- lifecycle FastAPI;
- endpoint individual;
- endpoint batch;
- filtros por categoria;
- eficiência batch;
- equivalência memória vs Chroma;
- avaliação de recuperação preservada.

## Limitações

- Chroma local não é arquitetura de produção distribuída;
- arquivos persistidos são locais;
- não há migração automática de coleção;
- trocar modelo de embedding exige reindexação;
- mudar o texto de embedding exige reindexação;
- não há coordenação entre múltiplos processos;
- não há health check específico do vector store;
- não há observabilidade de latência;
- não há telemetria de query;
- filtros ainda são limitados;
- não há busca híbrida;
- não há reranking;
- não há RAG;
- dataset sintético pequeno;
- ausência de dados reais;
- ausência de avaliação em escala.

## Próximos Passos

- RAG;
- recuperação com geração;
- fontes e citações;
- montagem de contexto;
- guardrails;
- observabilidade;
- estratégia de produção para armazenamento vetorial.
