# Progresso Da Semana 4

## Status Técnico

| Dia | Entrega técnica | Status |
|---|---|---|
| Dia 1 | Abstração `KnowledgeSearchBackend` e desacoplamento do serviço | Implementado |
| Dia 2 | `PersistentClient`, coleção Chroma e distância de cosseno | Implementado |
| Dia 3 | Indexação idempotente com `upsert` e estimativa de custo | Implementado |
| Dia 4 | Backend Chroma de leitura, update/delete e consulta direta | Implementado |
| Dia 5 | Endpoint usando Chroma via lifecycle da aplicação | Implementado |
| Dia 6 | Filtros por categoria, batch e endpoint batch | Implementado |
| Dia 7 | Equivalência, avaliação Chroma e fechamento documental | Implementado |

## Observações

- `KnowledgeVectorIndex` permanece como referência em memória para testes,
  avaliação e fallback explícito de desenvolvimento.
- O backend real do endpoint é Chroma persistente.
- Os testes automatizados usam coleções temporárias e não acessam a OpenAI.
- A coleção real local precisa ser indexada com 12 artigos antes de smoke tests
  reais ou avaliação Chroma real.

## DataCamp

O exercício final do Capítulo 3 deve ser revisado manualmente pelo estudante.
Este documento não marca o exercício como concluído automaticamente.
