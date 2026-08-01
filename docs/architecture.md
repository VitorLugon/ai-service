# Arquitetura

## Visão geral

O AI Service é uma API FastAPI independente para funcionalidades de IA usadas
por aplicações internas, inicialmente o HelpDeskLite.

```text
Cliente interno
        |
        | HTTP + X-API-Key
        v
FastAPI routes
        |
        v
Dependencies
        |
        v
Services
        |
        v
OpenAI Responses API
```

## Configuração

As configurações ficam em `app/core/config.py` e são carregadas por Pydantic
Settings. A dependência `get_settings()` usa cache para evitar recriações
desnecessárias durante a aplicação.

As variáveis relevantes para classificação são:

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_PROMPT_STRATEGY=one_shot
```

`OPENAI_PROMPT_STRATEGY` aceita `zero_shot`, `one_shot` e `few_shot`. O baseline
atual é `one_shot`.

O fluxo da estratégia é:

```text
OPENAI_PROMPT_STRATEGY
        |
        v
Settings
        |
        v
PromptStrategy
        |
        v
TicketClassifierService
        |
        v
build_ticket_classification_instructions()
```

Na API, `get_ticket_classifier` lê `Settings.openai_prompt_strategy` e entrega
essa estratégia ao `TicketClassifierService`.

## Estrutura de documentação

```text
docs/
├── architecture.md
└── evaluation.md
```

`docs/evaluation.md` registra o dataset sintético, métricas, resultados reais,
casos divergentes, ambiguidades e próximos passos.

## Classificação

`TicketClassifierService` recebe por injeção:

- cliente assíncrono da OpenAI;
- modelo;
- estratégia de prompt.

O service não lê `.env`, não conhece FastAPI e não expõe segredos. Ele chama
`responses.parse()` com `TicketClassificationResult`, preservando o contrato
estruturado validado por Pydantic.

## Estratégias

As estratégias ficam em `app/prompts/ticket_classification.py`:

- `zero_shot`: regras sem exemplos;
- `one_shot`: regras com um exemplo;
- `few_shot`: regras com vários exemplos.

`one_shot` é o baseline configurado neste ciclo. O relatório real mais recente
com 12 casos sintéticos e `gpt-5-mini` registrou empate entre as três
estratégias: 11/12 de acurácia conjunta. Antes de trocar o baseline, o dataset
deve ser ampliado e a comparação deve ser repetida.

`zero_shot` e `few_shot` continuam preservados para comparação manual. Não há
fallback automático entre estratégias.

## Avaliação

O Dia 6 adicionou uma camada de avaliação separada da classificação:

- `app/evaluation/dataset.py` carrega o dataset sintético;
- `app/schemas/evaluation.py` define `TicketEvaluationCase`,
  `TicketEvaluationItemResult` e `TicketEvaluationReport`;
- `app/services/ticket_evaluator.py` calcula as métricas;
- `scripts/evaluate_ticket_classifier.py` executa avaliações reais.

`TicketEvaluatorService` depende de um `Protocol`, não de uma classe concreta.
Esse contrato exige apenas:

- propriedade `model`;
- método assíncrono `classify()`.

Essa separação permite avaliar tanto o classificador real quanto
classificadores falsos nos testes, sem instanciar `AsyncOpenAI`.

O fluxo de avaliação é:

```text
evaluation/tickets.json
        |
        v
load_ticket_evaluation_cases
        |
        v
TicketEvaluatorService
        |
        v
TicketClassifierService
        |
        v
TicketEvaluationReport
```

O dataset em `evaluation/tickets.json` é sintético e pequeno. Ele valida
categorias, prioridades e fronteiras de decisão, mas não substitui uma base
maior com chamados reais anonimizados.

O relatório `TicketEvaluationReport` inclui:

- modelo;
- estratégia;
- total de casos;
- acertos por categoria;
- acertos por prioridade;
- acertos conjuntos;
- acurácia de categoria;
- acurácia de prioridade;
- acurácia conjunta;
- resultado individual de cada caso.

## Avaliações reais

As avaliações reais usam a OpenAI API e podem consumir créditos:

```powershell
python -m scripts.evaluate_ticket_classifier --strategy one_shot --limit 2
python -m scripts.evaluate_ticket_classifier --strategy one_shot
python -m scripts.evaluate_ticket_classifier --all-strategies
```

Elas não rodam no GitHub Actions porque dependem de chave secreta, acesso de
rede, disponibilidade externa, possível variação entre execuções e consumo
financeiro. Nesta fase, esses fatores não devem bloquear a integração contínua.
O CI executa somente testes determinísticos com mocks e classificadores falsos.

## Testes

Os testes automatizados:

- não leem a chave real;
- não acessam a internet;
- não instanciam `AsyncOpenAI` nos testes do evaluator;
- usam `_env_file=None` para isolar configurações;
- validam dataset, schemas, evaluator, prompts, API e erros do provedor.

O limite mínimo de cobertura permanece em 90%.

## Busca semântica

A Semana 3 introduz embeddings para representar consultas e artigos da base de
conhecimento como vetores numéricos. No Dia 4, esses vetores passaram a ser
usados por um índice vetorial em memória e por um serviço assíncrono de busca.

O fluxo implementado é:

```text
knowledge/articles.json
        |
        v
load_knowledge_articles
        |
        v
build_knowledge_article_embedding_text
        |
        v
EmbeddingService
        |
        v
KnowledgeVectorIndex
        |
        v
KnowledgeSearchService
        |
        v
list[KnowledgeSearchMatch]
```

O modelo de embeddings é configurável por:

```env
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

A função `cosine_similarity`, em `app/core/vector_math.py`, é independente da
OpenAI, da camada HTTP, de Pydantic Settings e de variáveis de ambiente. Ela
calcula a pontuação por produto escalar e norma dos vetores, rejeitando entradas
vazias, dimensões diferentes e vetores nulos.

Esta etapa não inclui:

- banco vetorial;
- persistência dos embeddings;
- endpoint HTTP de busca semântica;
- pipeline RAG;
- geração de resposta baseada em documentos;
- avaliação quantitativa da recuperação.

## EmbeddingService

`EmbeddingService`, em `app/services/embedding_service.py`, encapsula a geração
assíncrona de embeddings sem conhecer FastAPI, arquivos da base de conhecimento
ou persistência vetorial.

O fluxo do serviço é:

```text
Textos
        |
        v
EmbeddingService
        |
        v
OpenAI Embeddings API
        |
        v
Validação
        |
        v
list[list[float]]
```

Suas responsabilidades são:

- normalizar textos com remoção de espaços externos;
- gerar embeddings em lote;
- preservar a ordem das entradas;
- validar índices retornados pelo provedor;
- validar a quantidade de vetores;
- rejeitar vetores vazios;
- validar consistência de dimensões;
- rejeitar NaN e infinitos;
- traduzir falhas do SDK para exceções internas do provedor.

O serviço não carrega artigos, não calcula similaridade, não persiste vetores,
não realiza pesquisa, não expõe endpoint HTTP e não gera respostas RAG.

O fluxo experimental da base de conhecimento é:

```text
knowledge/articles.json
        |
        v
load_knowledge_articles
        |
        v
build_knowledge_article_embedding_text
        |
        v
EmbeddingService
        |
        v
embeddings temporários
```

Os vetores gerados por `scripts.embed_knowledge_base_smoke_test` são temporários
e não são gravados em disco.

A integração real com embeddings está disponível por meio de:

```powershell
python -m scripts.embedding_smoke_test
python -m scripts.embed_knowledge_base_smoke_test
```

Esses smoke tests usam a API real e não são executados pelo `pytest`.

## Base de conhecimento

A base de conhecimento sintética fica em:

```text
knowledge/articles.json
```

Ela é carregada e preparada para indexação futura pelo fluxo:

```text
knowledge/articles.json
        |
        v
load_knowledge_articles
        |
        v
KnowledgeArticle
        |
        v
build_knowledge_article_embedding_text
        |
        v
KnowledgeVectorIndex
```

A estrutura relacionada é:

```text
app/
├── knowledge/
│   ├── loader.py
│   ├── text.py
│   └── vector_index.py
├── services/
│   └── knowledge_search.py
└── schemas/
    └── knowledge.py

knowledge/
└── articles.json
```

`KnowledgeArticle` define o contrato dos artigos. Ele rejeita campos extras,
valida IDs em kebab-case minúsculo, normaliza espaços de título e conteúdo, e
normaliza palavras-chave para letras minúsculas. Keywords vazias são rejeitadas,
duplicatas são removidas preservando a primeira ocorrência e cada artigo deve
possuir ao menos uma palavra-chave.

`load_knowledge_articles` lê o arquivo local em UTF-8, valida a lista com
Pydantic, rejeita base vazia e rejeita IDs duplicados. Erros legítimos de JSON,
arquivo ou schema são preservados.

`build_knowledge_article_embedding_text` produz uma representação textual em
ordem estável:

```text
Título
Categoria
Palavras-chave
Conteúdo
```

O ID técnico não entra no texto de embedding. Alterar a composição ou a ordem
desse texto no futuro pode exigir reindexação dos documentos.

Os artigos são sintéticos e não contêm dados reais de clientes. A base atual tem
12 artigos, com dois artigos por categoria de chamado.

## Índice Vetorial

`KnowledgeVectorIndex`, em `app/knowledge/vector_index.py`, mantém artigos e
embeddings em memória. Ele recebe os vetores já calculados, normaliza os valores
para `float` e valida:

- existência de ao menos um artigo;
- mesma quantidade de artigos e embeddings;
- IDs de artigos sem duplicidade;
- embeddings não vazios;
- dimensões compatíveis;
- valores finitos;
- vetores não nulos.

O índice expõe `size` e `dimensions`. A busca recebe um embedding de consulta e
`top_k`, calcula similaridade de cosseno para cada artigo, limita os scores ao
intervalo aceito por `KnowledgeSearchMatch`, ordena por maior score e usa o ID
do artigo como desempate determinístico. Quando `top_k` é maior que a quantidade
de artigos, retorna todos os resultados disponíveis.

## Serviço de Busca

`KnowledgeSearchService`, em `app/services/knowledge_search.py`, coordena a
busca semântica sem depender diretamente de `AsyncOpenAI`. Ele recebe:

- um provedor assíncrono compatível com `TextEmbeddingProvider`;
- um `KnowledgeVectorIndex` já construído.

O contrato mínimo do provedor exige apenas `embed_text(text: str)`. Com isso, o
serviço pode usar `EmbeddingService` em smoke tests reais e provedores falsos
nos testes automatizados.

O fluxo do serviço é:

```text
query
        |
        v
strip()
        |
        v
TextEmbeddingProvider.embed_text()
        |
        v
KnowledgeVectorIndex.search()
        |
        v
list[KnowledgeSearchMatch]
```

Consultas vazias são rejeitadas antes de chamar o provedor de embeddings.

A busca real na base sintética pode ser exercitada com:

```powershell
python -m scripts.search_knowledge_base_smoke_test
```

Esse script usa a API real da OpenAI, gera embeddings temporários para os
artigos, constrói o índice em memória e executa uma consulta sintética com
resultados top-k. Ele não persiste vetores e não roda no `pytest`.
