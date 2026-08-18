# Semana 5 — Revisão Técnica

## Resultado

A Semana 5 fechou o pipeline RAG end-to-end mantendo as etapas separadas:

```text
Retrieval
    |
    v
Context Assembly
    |
    v
Prompt Assembly
    |
    v
Generation
    |
    v
Answer Composition
```

O endpoint interno `POST /internal/rag/answer` está disponível e protegido por
`X-API-Key`.

## Arquitetura Final

`RagService` é o orquestrador de aplicação. Ele não conhece FastAPI, `.env`,
Settings, Chroma concreto nem `AsyncOpenAI`. A dependência HTTP monta o pipeline
com:

- `KnowledgeSearchService`;
- `RagContextBuilder`;
- `RagPromptBuilder`;
- `RagGenerationService`;
- `RagAnswerComposer`.

Durante cada request, somente a query gera embedding. Os artigos precisam estar
previamente indexados no Chroma.

## Endpoint RAG

```http
POST /internal/rag/answer
```

Payload:

```json
{
  "query": "Redefini minha senha, mas ainda não consigo acessar minha conta. O que devo fazer?",
  "top_k": 3,
  "category": "acesso_e_autenticacao"
}
```

Resposta:

```json
{
  "answer": "Texto gerado pelo modelo.",
  "sources": [],
  "source_count": 0
}
```

`sources` vem exclusivamente das evidências passadas ao modelo, não de texto
arbitrário produzido pela geração.

## Grounding E Fontes

O prompt instrui o modelo a responder somente com o contexto recuperado e a
admitir falta de informação quando não houver evidência suficiente. O composer
preserva a resposta gerada, mas monta as fontes a partir de `RagContext.sources`.

Isso garante attribution controlada pela aplicação. Ainda não garante
verificação formal de cada afirmação contra uma fonte.

## Avaliação

`RagEvaluator` permanece fora do caminho HTTP. Ele mede retrieval, sources,
keyword coverage e comportamento de recusa com métricas determinísticas. Os
scripts reais usam OpenAI e podem consumir créditos; os testes automatizados
usam fakes.

## Resultados

A avaliação real pós-migração registrada pelo usuário indicou:

- artigos indexados: 12;
- consultas avaliadas: 18;
- Hit Rate@1: 1.0000;
- Recall@1: 0.8333;
- Hit Rate@3: 1.0000;
- Recall@3: 1.0000;
- Hit Rate@5: 1.0000;
- Recall@5: 1.0000;
- MRR: 1.0000.

Esses números refletem a base sintética atual e não substituem avaliação com
dados reais anonimizados.

## Problemas E Correções

- o pipeline existia em partes, mas não havia orquestrador de aplicação;
- não havia rota HTTP para resposta RAG completa;
- a documentação ainda tratava resposta RAG e endpoint como pendências;
- os testes não cobriam o caminho HTTP RAG end-to-end.

As correções adicionaram `RagService`, rota, dependência, schemas HTTP, smoke
test real controlado e testes com Chroma temporário e OpenAI falsa.

## Limitações E Próximos Passos

- não há streaming;
- não há reranking;
- a coleção Chroma ainda usa artigos inteiros, não chunks;
- não há verificação automática de citações por claim;
- não há avaliação LLM-as-a-judge;
- ainda falta integração com o backend do HelpDeskLite.
