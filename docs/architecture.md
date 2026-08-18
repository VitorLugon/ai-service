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
OPENAI_RAG_MODEL=gpt-5-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_PROMPT_STRATEGY=one_shot
RAG_CONTEXT_MAX_CHARACTERS=12000
RAG_CHUNK_SIZE_CHARACTERS=2000
RAG_CHUNK_OVERLAP_CHARACTERS=200
RAG_QUESTION_MAX_CHARACTERS=2000
RAG_MAX_OUTPUT_TOKENS=800
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

## Ciclo De Vida Da Aplicação

`app/main.py` cria a aplicação com lifespan. No startup, a API carrega os
recursos persistentes necessários para busca semântica e os guarda em
`ApplicationResources`, definido em `app/core/app_state.py`.

O fluxo de inicialização da busca é:

```text
FastAPI lifespan
        |
        v
Settings
        |
        v
PersistentClient
        |
        v
get_collection
        |
        v
ChromaKnowledgeSearchBackend
        |
        v
app.state.resources
```

Em produção, a coleção Chroma precisa existir, ter metadata compatível e conter
registros. Em testes, o factory da aplicação permite injetar um backend falso,
evitando acesso a `data/chroma` e chamadas externas.

## Estrutura de documentação

```text
docs/
├── architecture.md
├── evaluation.md
├── rag-evaluation.md
├── week-3-review.md
├── week-4-review.md
├── week-5-review.md
└── decisions/
```

`docs/evaluation.md` registra o dataset sintético, métricas, resultados reais,
casos divergentes, ambiguidades, avaliação de recuperação semântica e próximos
passos. As revisões semanais registram o estado técnico ao final de cada
marco, e `docs/decisions/` mantém as ADRs do projeto.

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

## Avaliação da Recuperação Semântica

O Dia 6 adiciona uma avaliação separada para a qualidade da busca semântica:

- `evaluation/knowledge_queries.json` define consultas sintéticas e artigos
  relevantes;
- `app/schemas/retrieval_evaluation.py` define os contratos da avaliação;
- `app/evaluation/retrieval_dataset.py` carrega e valida o dataset;
- `app/services/knowledge_retrieval_evaluator.py` calcula Hit Rate@k,
  Recall@k e MRR;
- `scripts/evaluate_knowledge_retrieval.py` executa uma avaliação real com a
  OpenAI API.

O fluxo é:

```text
evaluation/knowledge_queries.json
        |
        v
load_retrieval_evaluation_cases
        |
        v
EmbeddingProvider.embed_texts
        |
        v
KnowledgeVectorIndex.search(top_k=index.size)
        |
        v
KnowledgeRetrievalEvaluator
        |
        v
RetrievalEvaluationReport
```

A avaliação não chama o endpoint HTTP de busca. Ela trabalha diretamente com o
índice vetorial em memória e preserva o ranking completo de cada consulta para
calcular Mean Reciprocal Rank. Os embeddings das consultas são gerados em uma
única chamada em lote, e os testes usam provedores falsos sem acesso externo.

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
conhecimento como vetores numéricos. A Semana 4 adiciona persistência local no
Chroma para os embeddings dos artigos e integra o endpoint HTTP a esse backend.

O fluxo do endpoint HTTP é:

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
Chroma persistente
        |
        v
ChromaKnowledgeSearchBackend
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

O índice em memória permanece disponível para testes, avaliação e fallback
explícito de desenvolvimento. O endpoint HTTP usa Chroma persistente.

Filtros são representados por `KnowledgeSearchFilter`, em
`app/schemas/knowledge.py`. O schema conhece apenas conceitos de domínio, como
`category`, e não expõe a sintaxe `where` do Chroma para rotas ou clientes.

Essa recuperação alimenta tanto o endpoint de busca quanto o endpoint RAG.

## Pipeline RAG

A Semana 5 implementa o pipeline RAG mantendo Retrieval, Augmentation,
Generation e Answer Composition como etapas separadas. A montagem de contexto
não chama OpenAI, não acessa Chroma, não lê arquivos e não depende de FastAPI.

Retrieval:

```text
query
 |
 v
EmbeddingService
 |
 v
Chroma
 |
 v
KnowledgeSearchMatch[]
```

Augmentation:

```text
KnowledgeSearchMatch[]
 |
 v
RagContextBuilder
 |
 v
RagContext
 |
 v
RagPromptBuilder
 |
 v
RagPrompt
```

Generation:

```text
RagPrompt
 |
 v
RagGenerationService
 |
 v
OpenAI Responses API
 |
 v
RagGenerationResult
```

Answer Composition:

```text
RagGenerationResult
        +
RagContext.sources
        |
        v
RagAnswerComposer
        |
        v
RagAnswer
```

Retrieval é responsável por embeddings da query, filtros, busca e ranking.
Augmentation é responsável por preservar a ordem recebida, transformar os
matches em sources, montar um texto determinístico e respeitar o orçamento de
contexto configurado por `RAG_CONTEXT_MAX_CHARACTERS`.

`RagSource` preserva a evidência original completa: ID do artigo, título,
categoria, score, rank e conteúdo completo. `RagContext.text` contém somente o
texto formatado que será enviado à futura camada generativa e nunca excede o
orçamento configurado. Quando a primeira fonte sozinha excede o limite, apenas
o texto é truncado com marcador explícito; `RagSource.content` continua com o
conteúdo completo para auditoria, debugging e citações futuras.

O texto recuperado continua sendo tratado como conteúdo dentro da seção
`content:`. O prompt assembly adiciona instruções estáveis para que a futura
geração trate fontes como dados não confiáveis. Delimitadores textuais ajudam a
estrutura, mas não são uma barreira de segurança perfeita.

`RagService`, em `app/services/rag_service.py`, é o orquestrador de aplicação
do fluxo end-to-end. Ele recebe serviços por injeção e executa:

```text
KnowledgeSearchService.search()
        |
        v
RagContextBuilder.build()
        |
        v
RagPromptBuilder.build()
        |
        v
RagGenerationService.generate()
        |
        v
RagAnswerComposer.compose()
```

O serviço não instancia `AsyncOpenAI`, não lê Settings, não conhece FastAPI e
não acessa o Chroma diretamente. Erros das camadas internas são propagados para
os handlers HTTP já existentes.

## Grounded RAG Response

O Dia 5 une o texto gerado pelo modelo às fontes controladas pela aplicação:

```text
RagContext
     |
     +-----------------------+
     |                       |
     v                       v
RagPrompt               RagSource[]
     |                       |
     v                       |
Generation                   |
     |                       |
     v                       |
RagGenerationResult          |
     |                       |
     +-----------+-----------+
                 |
                 v
         RagAnswerComposer
                 |
                 v
             RagAnswer
```

O LLM controla:

- texto de `answer`.

A aplicação controla:

- `sources`;
- provenance de artigo/chunk;
- `source_id`;
- ordem das fontes.

`RagAnswerComposer` é síncrono, puro e determinístico. Ele não acessa OpenAI,
Chroma, FastAPI, arquivos ou Settings. O componente recebe `RagGenerationResult`
e `RagContext`, preserva `generation.answer` e monta `RagAnswer.sources` apenas
a partir de `RagContext.sources`.

`RagAnswerSource` expõe `source_id`, `article_id`, `chunk_id`, `title`,
`category` e `rank`. O `source_id` usa `chunk_id` quando a evidência veio de um
chunk; caso contrário usa `article_id`. Scores vetoriais e conteúdo completo
das fontes não são retornados automaticamente.

Fontes duplicadas são removidas por `source_id`, preservando a primeira
ocorrência e o rank original do contexto. Dois chunks diferentes do mesmo artigo
continuam sendo duas fontes distintas. Quando não há evidências, `RagAnswer`
mantém o texto gerado e retorna `sources=[]` com `source_count=0`.

As fontes retornadas significam evidências fornecidas à geração. Elas ainda não
representam citações verificadas por claim, e a aplicação não tenta resolver IDs
ou marcadores como `[SOURCE 999]` presentes no texto gerado pelo modelo.

## RAG Evaluation

O Dia 6 adiciona avaliação RAG fora do caminho de request da API. O evaluator
mede o resultado do pipeline, mas não participa da execução de produção.

```text
Question
   |
   v
RAG Pipeline
   |
   v
RagAnswer
   |
   v
RagEvaluator
   +--> Retrieval metrics
   +--> Source metrics
   +--> Answer coverage
   +--> Refusal behavior
```

O dataset versionado fica em `evaluation/rag_cases.json` e contém casos com
resposta esperada, casos sem evidência e casos com múltiplas fontes relevantes.
O carregador valida IDs únicos, perguntas únicas, consistência entre
comportamento esperado e artigos relevantes, keywords esperadas e referências a
artigos existentes em `knowledge/articles.json`.

`RagEvaluator` depende de um pipeline abstrato que retorna os IDs recuperados e
um `RagAnswer`. Em testes e no script offline, esse pipeline é fake e
determinístico. No script real, o wiring usa `KnowledgeSearchService`,
`RagContextBuilder`, `RagPromptBuilder`, `RagGenerationService` e
`RagAnswerComposer`.

As métricas determinísticas são:

- `retrieval_hit`: ao menos um artigo relevante apareceu no retrieval em casos
  com resposta esperada;
- `source_hit`: ao menos um artigo relevante apareceu em `RagAnswer.sources`;
- `answer_keyword_coverage`: fração de keywords esperadas encontradas na
  resposta;
- `correct_refusal`: caso sem evidência respondeu como falta de informação;
- `false_refusal`: caso com resposta esperada recusou por falta de informação;
- `unsupported_answer`: caso sem evidência e sem sources retornou resposta
  substantiva.

Para os casos com resposta esperada, o relatório também inclui métricas de
recuperação em k e MRR com a mesma semântica da avaliação de retrieval. A
detecção de recusa é heurística e a cobertura de keywords não mede correção
factual profunda, entailment ou citações verificadas por claim.

## Chunking Do Contexto RAG

O Dia 2 da Semana 5 adiciona preparação determinística de chunks para a camada
de Augmentation. A arquitetura atual continua indexando documentos inteiros no
Chroma, mas o projeto já possui a estrutura para dividir artigos em trechos
rastreáveis antes da seleção de contexto.

Fluxo futuro:

```text
KnowledgeArticle
      |
      v
RagTextChunker
      |
      v
RagChunk[]
      |
      v
ranking / selection
      |
      v
RagContextBuilder
      |
      v
RagContext
```

`KnowledgeArticle` é o documento de origem. `RagChunk` é um trecho derivado de
um artigo e preserva `article_id`, título, categoria, `chunk_index`, `chunk_id`
determinístico e conteúdo. `RagSource` é a evidência selecionada para o
contexto final; quando nasce de chunk, também preserva `chunk_index` e
`chunk_id`.

O `RagTextChunker` é síncrono e puro. Ele normaliza quebras de linha de forma
conservadora, prefere separar por parágrafos, depois por quebras de linha,
depois por espaços e usa corte por caracteres apenas como fallback. O tamanho
do chunk é configurado por `RAG_CHUNK_SIZE_CHARACTERS`, e o overlap por
`RAG_CHUNK_OVERLAP_CHARACTERS`. A configuração rejeita `overlap` maior ou igual
ao tamanho do chunk.

O orçamento final de contexto continua sendo `RAG_CONTEXT_MAX_CHARACTERS`. O
builder preserva o ranking recebido, adiciona chunks inteiros enquanto couberem,
ignora duplicatas exatas de `chunk_id` e só trunca quando a primeira evidência
sozinha ultrapassa o orçamento.

Ainda não houve reindexação da coleção Chroma para chunks. Essa migração exige
decisão explícita, nova estratégia de indexação, revisão de schema e nova
avaliação de retrieval.

## Prompt Assembly

O Dia 3 da Semana 5 adiciona um contrato explícito para a geração RAG:

```text
RagContext
   |
   v
RagPromptBuilder
   |
   +--> system_instructions
   |
   +--> user_message
   |
   v
RagPrompt
```

`RagPromptBuilder` é síncrono, puro e independente de OpenAI, Chroma, FastAPI,
arquivos e Settings. O limite da pergunta é recebido por construtor e vem da
configuração `RAG_QUESTION_MAX_CHARACTERS` quando houver wiring futuro.

### System instructions

Contêm:

- função do assistente;
- grounding no contexto recuperado;
- comportamento quando não houver evidência suficiente;
- tratamento do conteúdo recuperado como dado não confiável.

Não contêm:

- pergunta;
- documentos;
- scores;
- IDs ou metadados dinâmicos de retrieval.

### User message

Contém seções determinísticas:

```text
=== CONTEXTO ===

...

=== PERGUNTA ===

...
```

Quando `RagContext.text` está vazio, a seção de contexto recebe uma mensagem
explícita de que nenhuma fonte relevante foi recuperada. A pergunta recebe
somente `strip()`; perguntas vazias ou acima do limite são rejeitadas sem
truncagem.

O builder usa `RagContext.text`, não o conteúdo completo de `RagSource`,
preservando a seleção, o truncamento e o orçamento definidos anteriormente pelo
context builder. Scores permanecem fora do texto enviado ao futuro modelo.

## Generation

O Dia 4 da Semana 5 adiciona a primeira camada concreta de geração RAG:

```text
RagPrompt
   |
   v
RagGenerationService
   |
   v
OpenAI Responses API
   |
   v
RagGenerationResult
```

O serviço recebe um prompt pronto, chama `client.responses.create()`, envia
`system_instructions` como `instructions`, envia `user_message` como `input`,
limita a saída por `RAG_MAX_OUTPUT_TOKENS`, usa `store=False` e extrai a
resposta por `response.output_text`.

`RagGenerationService` é responsável por:

- receber prompt pronto;
- chamar provider;
- validar resposta textual;
- rejeitar resposta vazia;
- rejeitar status incompleto ou não concluído quando informado pelo SDK;
- traduzir erros do provider para exceções internas;
- retornar `RagGenerationResult`.

Ele não:

- recupera artigos;
- monta contexto;
- decide ranking;
- acessa Chroma;
- constrói prompt;
- usa tools;
- usa `previous_response_id`;
- persiste resposta.

O fluxo conceitual atual é:

```text
Retrieval
    |
    v
Augmentation
    |
    v
Prompt Assembly
    |
    v
Generation
```

O modelo RAG é configurado por `OPENAI_RAG_MODEL`, separado do modelo de
classificação para permitir evolução independente. A camada não implementa
streaming e não retorna citações formais verificadas por claim.

## API RAG

O Dia 7 expõe o pipeline completo pela rota interna:

```http
POST /internal/rag/answer
```

A rota fica em `app/api/routes/rag.py`, usa a autenticação interna por
`X-API-Key` e delega para `RagService`. Ela não calcula similaridade, não monta
prompt manualmente, não executa avaliação e não reconstrói embeddings dos
artigos.

Os contratos Pydantic ficam em `app/schemas/rag.py`:

- `RagAnswerRequest`: recebe `query`, `top_k` e `category`, remove espaços
  externos da pergunta, rejeita campos extras, limita `top_k` entre 1 e 10 e
  limita a pergunta a 2000 caracteres;
- `RagAnswerResponse`: retorna `answer`, `sources` e `source_count`.

A dependência `get_rag_service`, em `app/api/dependencies/rag.py`, é
responsável por:

- obter o backend de busca já inicializado no lifespan;
- validar `OPENAI_API_KEY`;
- criar um cliente `AsyncOpenAI` por request;
- montar `EmbeddingService`, `KnowledgeSearchService`, `RagContextBuilder`,
  `RagPromptBuilder`, `RagGenerationService` e `RagAnswerComposer`;
- fechar o cliente assíncrono ao final da requisição.

Durante a request, somente a query é enviada ao provedor de embeddings. O
retrieval usa o Chroma persistente carregado no startup e os artigos já
indexados. A geração usa OpenAI Responses API com `store=False`.

Erros de provedor são convertidos para `502`, `503` ou `504` pelos handlers
globais. Erros do armazenamento de conhecimento são convertidos para `503`.

O fluxo HTTP atual é:

```text
POST /internal/rag/answer
        |
        v
RagAnswerRequest
        |
        v
RagService
        |
        v
RagAnswerResponse
```

## Estado Atual Da Recuperação Semântica

A recuperação semântica está funcional de ponta a ponta:

- a base sintética é carregada de `knowledge/articles.json`;
- os artigos são convertidos para uma representação textual estável;
- `EmbeddingService` gera embeddings em lote;
- `KnowledgeVectorIndex` mantém um índice linear em memória;
- `KnowledgeSearchService` executa busca top-k;
- `POST /internal/knowledge/search` expõe a busca como endpoint interno
  protegido usando Chroma persistente;
- `KnowledgeRetrievalEvaluator` avalia diretamente os serviços, sem passar pela
  camada HTTP;
- as consultas de avaliação são processadas em lote;
- o MRR usa o ranking completo retornado pelo índice.

Os embeddings dos artigos são persistidos pelo script de indexação da Semana 4.
O índice em memória não é mais reconstruído pelo endpoint HTTP.

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
busca semântica sem depender diretamente de `AsyncOpenAI` nem de uma
implementação concreta de índice. Ele recebe:

- um provedor assíncrono compatível com `EmbeddingProvider`;
- um backend compatível com `KnowledgeSearchBackend`.

O contrato do provedor expõe `model`, `embed_text(text: str)` e
`embed_texts(texts)`. Com isso, a busca usa `EmbeddingService` em smoke tests
reais e provedores falsos nos testes automatizados.

O fluxo do serviço é:

```text
query
        |
        v
strip()
        |
        v
EmbeddingProvider.embed_text()
        |
        v
KnowledgeVectorIndex.search()
        |
        v
list[KnowledgeSearchMatch]
```

Consultas vazias são rejeitadas antes de chamar o provedor de embeddings.

## Abstração do mecanismo de busca

A Semana 4 prepara a busca semântica para armazenamento vetorial persistente
sem alterar o comportamento do endpoint HTTP:

```text
KnowledgeSearchService
          |
          v
KnowledgeSearchBackend
       /             \
      v               v
KnowledgeVectorIndex  ChromaKnowledgeSearchBackend
 avaliação/testes     endpoint HTTP
```

`KnowledgeSearchBackend`, em `app/knowledge/search_backend.py`, é um contrato de
leitura. Ele expõe apenas:

- `size`: quantidade de artigos disponíveis;
- `search(query_embedding, top_k=...)`: recuperação semântica estruturada.

Operações de escrita, persistência, reset, upsert ou exclusão não pertencem a
esse contrato. `KnowledgeVectorIndex` continua compatível por tipagem
estrutural, sem herdar explicitamente do protocolo, e permanece útil para
avaliação e testes. O endpoint HTTP usa `ChromaKnowledgeSearchBackend`
inicializado no lifespan da aplicação.

`EmbeddingService` continua responsável por gerar vetores. O backend de busca
recebe o embedding da consulta já calculado e retorna `KnowledgeSearchMatch`.

## Integração Chroma local

O módulo `app/knowledge/chroma.py` concentra a fronteira com o SDK do Chroma.
Ele cria um `PersistentClient` local, garante a existência do diretório
`data/chroma`, obtém ou cria a coleção `helpdesklite-knowledge-v1` com distância
de cosseno e valida a metadata esperada:

- descrição da coleção;
- versão de schema;
- modelo de embeddings usado pela aplicação.

A coleção é criada com `embedding_function=None`. O Chroma não gera embeddings,
não usa `OpenAIEmbeddingFunction` e não baixa modelo local. Os vetores são
fornecidos explicitamente pela aplicação.

O script `scripts/inspect_chroma_collection.py` usa as configurações da
aplicação para criar ou validar a coleção persistente local e imprimir sua
contagem, sem indexar artigos.

O fluxo de leitura da API usa `app/knowledge/chroma_runtime.py`. Ele cria o
`PersistentClient`, chama `get_collection` com `embedding_function=None`, valida
schema/modelo na metadata e rejeita coleção ausente ou vazia. Esse runtime não
usa `get_or_create_collection`, não indexa artigos e não faz `upsert`.

## Indexação Idempotente

O Dia 3 adiciona a preparação determinística dos 12 artigos para persistência:

- `app/services/embedding_cost.py` conta tokens com `tiktoken` e estima custo
  com `Decimal`;
- `app/schemas/knowledge_indexing.py` define os registros e metadados que serão
  persistidos;
- `app/knowledge/indexing.py` transforma `KnowledgeArticle` em registro de
  indexação, preservando IDs, conteúdo original e `keywords_json`
  determinístico;
- `app/services/knowledge_indexer.py` gera embeddings em lote e persiste com
  `collection.upsert`.

O ID do Chroma é sempre `KnowledgeArticle.id`. A metadata persistida inclui
título, categoria, palavras-chave em JSON determinístico, versão de schema e
modelo de embeddings. A ausência de timestamp e UUID mantém a indexação
reprodutível.

O script `scripts/index_knowledge_base.py` calcula a estimativa de tokens/custo
antes da chamada real à OpenAI, gera embeddings em lote via `EmbeddingService` e
faz `upsert` dos registros. Executar o script novamente não duplica os artigos:
os mesmos IDs são atualizados.

## Leitura E Manutenção Do Chroma

O Dia 4 adiciona `app/knowledge/chroma_backend.py` como implementação
persistente do contrato `KnowledgeSearchBackend`. O backend recebe uma coleção
Chroma já configurada, não abre cliente, não carrega settings, não lê arquivos e
não gera embeddings.

Na busca, o backend:

- valida o embedding recebido;
- limita `n_results` ao tamanho da coleção;
- chama `collection.query` com `query_embeddings` explícito;
- envia `where` quando existe filtro de categoria;
- solicita apenas documentos, metadatas e distâncias;
- reconstrói `KnowledgeArticle` a partir de ID, documento e metadata;
- converte distância de cosseno para similaridade com `score = 1 - distance`;
- preserva a ordem retornada pelo Chroma.

Respostas incompletas ou inconsistentes do Chroma são rejeitadas com erro claro.
O backend não interpreta distância como similaridade sem conversão.

O Dia 6 adiciona `search_filtered()` e `search_many()` ao backend concreto sem
alterar o protocolo básico `KnowledgeSearchBackend`. A busca individual delega
para a validação comum em lote quando apropriado. Em batch, a resposta do Chroma
é validada em duas camadas:

- quantidade externa igual à quantidade de queries;
- quantidades internas consistentes entre IDs, documentos, metadatas e
  distâncias para cada query.

O filtro de categoria é convertido para:

```python
{"category": {"$eq": "<valor-do-enum>"}}
```

Esse dicionário é montado somente na camada de infraestrutura Chroma.

O serviço `app/services/knowledge_collection_service.py` concentra manutenção
por ID. Atualizações verificam a existência com `collection.get(ids=[...])`,
regeneram o embedding via `EmbeddingService` ou provedor compatível e persistem
com `upsert` usando o mesmo ID. Remoções verificam existência, chamam
`collection.delete(ids=[...])` e confirmam que a contagem diminuiu em 1.

Essas capacidades complementam o backend persistente usado pelo endpoint HTTP,
mas atualização e remoção ainda não são expostas como rotas.

## Decisão arquitetural

A decisão de usar Chroma futuramente está registrada em:

```text
docs/decisions/0001-use-chroma-vector-store.md
```

Essa decisão agora está implementada no fluxo de leitura do endpoint: Chroma
está instalado, a coleção local persistente pode ser criada e validada, e os
arquivos em `data/chroma` não são versionados. A indexação persistente existe
como script explícito e idempotente. Leitura, atualização e remoção por ID já
existem em serviços desacoplados; o endpoint HTTP consulta a coleção Chroma já
indexada.

## API de Busca

O Dia 5 expõe a busca semântica pela rota interna:

```http
POST /internal/knowledge/search
```

A rota fica em `app/api/routes/knowledge.py`, usa a mesma autenticação interna
por `X-API-Key` das demais rotas internas e delega a busca para
`KnowledgeSearchService`. Ela não calcula similaridade diretamente, não cria
uma segunda regra de autenticação e não reconstrói embeddings dos artigos.

Os contratos Pydantic ficam em `app/schemas/knowledge.py`:

- `KnowledgeSearchRequest`: recebe `query` e `top_k`, remove espaços externos
  da consulta, rejeita campos extras e limita `top_k` entre 1 e 10;
- `KnowledgeSearchResponse`: retorna a consulta normalizada, o modelo de
  embeddings, a quantidade de artigos na coleção persistente e a lista de
  `KnowledgeSearchMatch`.

A dependência `get_knowledge_search_backend`, em
`app/api/dependencies/knowledge_search.py`, obtém o backend já inicializado em
`app.state.resources`. Ela não lê settings, não abre cliente Chroma, não carrega
JSON e não gera embeddings.

A dependência `get_knowledge_search_service`, em
`app/api/dependencies/knowledge_search.py`, é responsável por:

- obter o backend persistente do estado da aplicação;
- validar a configuração da OpenAI;
- criar `EmbeddingService`;
- disponibilizar `KnowledgeSearchService`;
- fechar o cliente assíncrono da OpenAI ao final da requisição.

Durante a requisição, `KnowledgeSearchService` chama
`EmbeddingService.embed_text()` somente para a query e repassa o embedding ao
`ChromaKnowledgeSearchBackend`. O backend consulta a coleção com
`query_embeddings` explícito; o Chroma não gera embeddings.

Quando `category` é informado no request, a rota cria `KnowledgeSearchFilter` e
o serviço usa a capacidade filtrada do backend por protocolo, sem depender da
classe concreta do Chroma.

## API de Busca Em Lote

O Dia 6 adiciona:

```http
POST /internal/knowledge/search/batch
```

O endpoint usa a mesma autenticação interna por `X-API-Key`. O request contém
`queries`, `top_k` e `category` opcional. O lote aceita de 1 a 20 consultas, e
cada consulta é normalizada antes da geração de embeddings.

O fluxo é:

```text
KnowledgeBatchSearchService
        |
        v
EmbeddingService.embed_texts(queries)
        |
        v
ChromaKnowledgeSearchBackend.search_many()
        |
        v
collection.query(query_embeddings=[...])
        |
        v
KnowledgeBatchSearchResponse
```

O serviço batch valida a quantidade de embeddings e a quantidade de rankings
retornados, preservando a ordem das queries. Ele exige backend com capacidade
`search_many()` por protocolo e não chama `embed_text()` em loop.

Esse desenho mantém a camada HTTP separada da lógica de similaridade e permite
que os testes substituam a dependência por um serviço falso, sem instanciar
`AsyncOpenAI` e sem acessar rede.

A busca real no endpoint exige coleção indexada previamente:

```powershell
python -m scripts.index_knowledge_base
```

O smoke test em memória `scripts.search_knowledge_base_smoke_test` continua
disponível para validações manuais separadas. Ele não representa o fluxo atual
do endpoint HTTP.

## Estado Ao Final Da Semana 4

Chroma é o backend real da API de busca semântica. Os artigos são indexados
previamente por script, e a aplicação reutiliza o backend carregado no lifespan.
Durante requests, apenas as queries geram embeddings sob demanda.

`KnowledgeVectorIndex` permanece como implementação de referência em memória
para testes, avaliação determinística e fallback explícito de desenvolvimento.
A avaliação de recuperação continua separada da camada HTTP e pode usar tanto o
índice em memória quanto um backend compatível com `KnowledgeSearchBackend`.

Indexação:

```text
KnowledgeArticle[]
        |
        v
EmbeddingService
        |
        v
Chroma upsert
```

Consulta:

```text
HTTP
        |
        v
EmbeddingService
        |
        v
Chroma query
        |
        v
KnowledgeSearchMatch[]
```

Funcionalidades ativas no fechamento:

- busca individual no Chroma;
- filtros por categoria;
- busca em lote;
- `embedding_function=None`;
- update/delete por serviço interno;
- comparação determinística entre memória e Chroma;
- script de avaliação Chroma sem reindexação de artigos.

## Estado Ao Final Da Semana 5

O pipeline RAG está funcional de ponta a ponta:

- retrieval persistente com Chroma;
- filtro opcional por categoria;
- montagem determinística de contexto;
- contrato explícito de prompt;
- geração com OpenAI Responses API;
- resposta final com fontes controladas pela aplicação;
- orquestração por `RagService`;
- endpoint interno `POST /internal/rag/answer`;
- avaliação RAG fora do caminho HTTP;
- smoke test real controlado em `scripts/rag_end_to_end_smoke_test.py`.

Ainda estão fora do escopo implementado:

- streaming;
- LangChain;
- banco vetorial remoto;
- reranking;
- verificação automática de citações por claim;
- reindexação da coleção Chroma por chunks.
