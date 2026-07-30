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

A Semana 3 introduz embeddings para representar chamados e artigos da base de
conhecimento como vetores numéricos.

A lógica inicial segue o fluxo:

```text
Texto
        |
        v
Embedding
        |
        v
cosine_similarity
        |
        v
Pontuação de relevância
```

O modelo de embeddings é configurável por:

```env
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

A função `cosine_similarity`, em `app/core/vector_math.py`, é independente da
OpenAI, da camada HTTP, de Pydantic Settings e de variáveis de ambiente. Ela
calcula a pontuação por produto escalar e norma dos vetores, rejeitando entradas
vazias, dimensões diferentes e vetores nulos.

A integração real com embeddings está disponível inicialmente por meio de:

```powershell
python -m scripts.embedding_smoke_test
```

Esse smoke test usa a API real e não é executado pelo `pytest`. Posteriormente,
a geração de embeddings deve ser encapsulada em um service específico e usada
por um índice da base de conhecimento.

Esta etapa ainda não inclui:

- banco vetorial;
- endpoint de busca semântica;
- pipeline RAG;
- geração de resposta baseada em documentos;
- base de conhecimento definitiva.

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
```

A estrutura relacionada é:

```text
app/
├── knowledge/
│   ├── loader.py
│   └── text.py
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

Os artigos são sintéticos e não contêm dados reais de clientes. Nesta etapa não
há persistência vetorial, endpoint de busca semântica ou geração RAG.
