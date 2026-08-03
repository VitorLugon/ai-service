# Revisão da Semana 3

## Objetivo

A Semana 3 implementou os fundamentos de recuperação semântica para a base de
conhecimento sintética do HelpDeskLite, conectando embeddings, índice vetorial
em memória, endpoint interno e avaliação quantitativa da recuperação.

## Funcionalidades entregues

- configuração do modelo de embeddings;
- similaridade de cosseno;
- base sintética de conhecimento;
- schemas e carregamento dos artigos;
- preparação textual estável dos artigos;
- `EmbeddingService`;
- embeddings em lote;
- índice vetorial em memória;
- busca top-k;
- serviço de busca;
- endpoint interno protegido;
- autenticação por API Key interna;
- dataset de avaliação da recuperação;
- Hit Rate@k;
- Recall@k;
- Mean Reciprocal Rank.

## Fluxo implementado

```text
Consulta
   |
   v
EmbeddingService
   |
   v
KnowledgeVectorIndex
   |
   v
KnowledgeSearchMatch[]
   |
   v
Endpoint ou avaliação
```

## Dataset

- 12 artigos sintéticos em `knowledge/articles.json`;
- 18 consultas sintéticas em `evaluation/knowledge_queries.json`;
- 12 consultas com um artigo relevante;
- 6 consultas com dois artigos relevantes;
- todos os 12 artigos aparecem ao menos uma vez como relevantes.

## Baseline

Baseline real executado em 2026-08-03 com `text-embedding-3-small`.

| Métrica | Resultado |
|---|---:|
| Hit Rate@1 | 1,0000 |
| Hit Rate@3 | 1,0000 |
| Hit Rate@5 | 1,0000 |
| Recall@1 | 0,8333 |
| Recall@3 | 1,0000 |
| Recall@5 | 1,0000 |
| MRR | 1,0000 |

## Casos analisados

- casos corretos no top 1: 18;
- casos cujo relevante ficou no top 3: 18;
- casos abaixo do top 3: 0;
- casos sem relevante recuperado: 0;
- causas encontradas: nenhum caso problemático no baseline real.

O Recall@1 ficou abaixo de 1,0000 porque há consultas com dois artigos
relevantes, e o top 1 só consegue conter um deles.

## Decisões

- nenhuma alteração no dataset;
- nenhuma alteração nos artigos;
- nenhuma alteração na representação textual dos artigos;
- nenhuma correção de implementação necessária;
- nenhum ajuste artificial por métrica foi feito.

O baseline foi preservado porque os resultados não indicaram ground truth
incorreto, conteúdo insuficiente, consulta problemática, representação
inadequada ou erro técnico.

## Limitações atuais

- artigos sintéticos;
- índice em memória;
- embeddings sem persistência;
- reconstrução do índice conforme o ciclo de vida atual;
- busca linear O(n);
- ausência de filtro por categoria;
- ausência de threshold mínimo;
- ausência de banco vetorial;
- ausência de resposta RAG;
- ausência de dados reais.

## Débitos técnicos

- índice reconstruído por requisição;
- custo de reprocessar artigos;
- caminho relativo da base;
- ausência de cache;
- ausência de persistência;
- ausência de filtros;
- ausência de métricas por categoria;
- dataset pequeno;
- ausência de comparação entre modelos;
- ausência de observabilidade específica da recuperação.

## Próximos passos

- estudar bancos vetoriais;
- avaliar persistência;
- usar metadados;
- implementar filtros;
- resolver ciclo de vida do índice;
- preparar pipeline RAG;
- avaliar recuperação antes da geração.
