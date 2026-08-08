# AI Service

API independente construída com Python e FastAPI para fornecer funcionalidades de inteligência artificial a aplicações internas.

O serviço será inicialmente integrado ao HelpDeskLite e poderá ser reutilizado por outros projetos.

## Funcionalidades atuais

- endpoint de saúde da aplicação;
- endpoint de prontidão;
- configuração por variáveis de ambiente;
- autenticação interna por API Key;
- integração com a OpenAI Responses API;
- classificação automática de chamados;
- saída estruturada validada com Pydantic;
- categoria, prioridade, resumo e tags;
- endpoint protegido para classificação;
- estratégias zero-shot, one-shot e few-shot;
- tratamento de entradas incompatíveis;
- exceções próprias para falhas do provedor;
- tratamento de timeout e falhas de conexão;
- tratamento de rate limit;
- tratamento de autenticação e configuração inválidas;
- tratamento de respostas incompletas;
- tratamento de recusas do modelo;
- respostas HTTP padronizadas;
- documentação automática com OpenAPI e Swagger UI;
- testes automatizados sem consumo da API;
- configuração de modelo de embeddings;
- geração assíncrona de embeddings;
- geração de embeddings em lote;
- validação dos vetores retornados pelo provedor;
- similaridade de cosseno;
- base de conhecimento sintética e versionada;
- validação de artigos com Pydantic;
- categorias e palavras-chave para artigos;
- representação textual estável para embeddings;
- índice vetorial em memória;
- armazenamento vetorial persistente local com Chroma;
- indexação idempotente dos artigos com `upsert`;
- busca semântica por similaridade de cosseno;
- endpoint de busca integrado ao Chroma persistente;
- filtro de busca por categoria sem expor `where` do Chroma;
- busca semântica em lote com embeddings das queries em uma única chamada;
- recuperação de resultados top-k;
- ordenação determinística em caso de empate;
- serviço de busca desacoplado do cliente da OpenAI;
- avaliação da recuperação semântica com Hit Rate@k, Recall@k e MRR;
- cobertura mínima de testes;
- lint e formatação com Ruff;
- análise estática com mypy;
- integração contínua com GitHub Actions.

## Tecnologias

- Python 3.12
- FastAPI
- OpenAI Python SDK
- OpenAI Responses API
- Chroma
- Pydantic
- pydantic-settings
- pytest
- pytest-cov
- Ruff
- mypy
- GitHub Actions

## Arquitetura

```text
ai-service/
├── app/
│   ├── api/
│   │   ├── dependencies/  # Construção e injeção de dependências
│   │   ├── routes/        # Endpoints HTTP
│   │   ├── exception_handlers.py
│   │   └── router.py
│   ├── core/              # Configurações, segurança e exceções
│   ├── knowledge/         # Carregamento, texto, Chroma e índices de busca
│   ├── prompts/           # Estratégias e instruções
│   ├── schemas/           # Contratos Pydantic
│   ├── services/          # Regras e integrações
│   └── main.py            # Criação da aplicação
├── docs/                  # Documentação da arquitetura
├── knowledge/             # Base de conhecimento sintética
├── scripts/               # Instalação, execução e smoke tests
└── tests/                 # Testes automatizados
```

A descrição completa está em [`docs/architecture.md`](docs/architecture.md).
Os resultados e limites da avaliação estão em
[`docs/evaluation.md`](docs/evaluation.md).
A revisão técnica da Semana 3 está em
[`docs/week-3-review.md`](docs/week-3-review.md).

## Requisitos

- Python 3.12
- Git
- PowerShell
- chave da OpenAI API para executar funcionalidades reais de inteligência artificial

As rotas `/health` e `/ready` funcionam sem uma chave da OpenAI.

## Instalação no Windows

Clone o repositório:

```powershell
git clone https://github.com/VitorLugon/ai-service.git
cd ai-service
```

Execute o script:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
```

O script:

- cria o ambiente virtual;
- atualiza o pip;
- instala as dependências;
- cria o `.env` a partir do `.env.example`, quando necessário.

## Variáveis de ambiente

As configurações locais devem ser armazenadas no `.env`.

```env
APP_NAME=AI Service
APP_VERSION=0.1.0
ENVIRONMENT=development

INTERNAL_API_KEY=sua-chave-interna

OPENAI_API_KEY=sua-chave-da-openai
OPENAI_MODEL=gpt-5-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_COST_PER_MILLION_TOKENS_USD=0.02
OPENAI_PROMPT_STRATEGY=one_shot

CHROMA_PERSIST_DIRECTORY=data/chroma
CHROMA_COLLECTION_NAME=helpdesklite-knowledge-v1
CHROMA_SCHEMA_VERSION=1
```

### Chave interna

A variável `INTERNAL_API_KEY` protege os endpoints internos.

Gere uma chave segura com:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Depois de modificar o `.env`, reinicie a aplicação.

### OpenAI API

A variável `OPENAI_API_KEY` deve receber uma chave válida da OpenAI API.

A variável `OPENAI_MODEL` determina o modelo utilizado:

```env
OPENAI_API_KEY=sua-chave-da-openai
OPENAI_MODEL=gpt-5-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_COST_PER_MILLION_TOKENS_USD=0.02
OPENAI_PROMPT_STRATEGY=one_shot
```

O modelo pode ser alterado sem modificar o código-fonte.
`OPENAI_EMBEDDING_MODEL` define o modelo utilizado para gerar embeddings.
`OPENAI_EMBEDDING_COST_PER_MILLION_TOKENS_USD` define uma referência
configurável para estimar custo antes de chamadas reais de embeddings.

A variável `OPENAI_PROMPT_STRATEGY` define a estratégia de prompt. Os valores
permitidos são:

- `zero_shot`;
- `one_shot`;
- `few_shot`.

O baseline atual é `one_shot`.

### Chroma local

As configurações do armazenamento vetorial local possuem valores padrão:

```env
CHROMA_PERSIST_DIRECTORY=data/chroma
CHROMA_COLLECTION_NAME=helpdesklite-knowledge-v1
CHROMA_SCHEMA_VERSION=1
```

`CHROMA_PERSIST_DIRECTORY` define o diretório persistente local do Chroma.
`CHROMA_COLLECTION_NAME` define a coleção da base de conhecimento.
`CHROMA_SCHEMA_VERSION` identifica a versão do schema validada na metadata da
coleção.

Nunca coloque uma chave real:

- no `.env.example`;
- no README;
- diretamente no código;
- em commits;
- em capturas de tela.

## Executar localmente

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev.ps1
```

Aplicação:

```text
http://127.0.0.1:8000
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

ReDoc:

```text
http://127.0.0.1:8000/redoc
```

## Endpoints

| Método | Endpoint | Autenticação | Descrição |
|---|---|---|---|
| GET | `/health` | Não | Verifica se o processo está funcionando |
| GET | `/ready` | Não | Verifica se o serviço está pronto |
| GET | `/internal/ping` | API Key | Valida a autenticação interna |
| POST | `/internal/tickets/classify` | API Key | Classifica um chamado usando IA |
| POST | `/internal/knowledge/search` | API Key | Busca artigos da base de conhecimento por similaridade semântica |
| POST | `/internal/knowledge/search/batch` | API Key | Busca semântica em lote na base de conhecimento |

## Autenticação interna

Endpoints internos exigem:

```text
X-API-Key: sua-chave
```

Teste de autenticação:

```powershell
curl.exe `
  -H "X-API-Key: SUA_CHAVE" `
  http://127.0.0.1:8000/internal/ping
```

Resposta:

```json
{
  "status": "ok",
  "message": "Internal authentication succeeded."
}
```

As rotas `/health` e `/ready` são públicas.

## Testar a conexão com a OpenAI

Configure o `.env` e execute:

```powershell
python -m scripts.openai_smoke_test
```

Resultado esperado:

```text
Modelo: gpt-5-mini
Resposta: ok
```

Esse comando utiliza a API real e pode consumir créditos.

## Testar embeddings

Embeddings representam textos como vetores numéricos. A Semana 3 usa esses
vetores para busca semântica em memória, comparando consultas e artigos com
similaridade de cosseno. A Semana 4 adiciona persistência local no Chroma para
os embeddings dos artigos. O Chroma recebe vetores explícitos da aplicação e não
usa função própria de embeddings.

Configure o `.env` e execute:

```powershell
python -m scripts.embedding_smoke_test
```

O smoke test usa o `EmbeddingService`, envia textos sintéticos para a API real,
usa o modelo definido em `OPENAI_EMBEDDING_MODEL` e compara se dois textos sobre
acesso/senha ficam mais próximos entre si do que de um texto sobre alteração de
plano.

Para processar temporariamente a base de conhecimento:

```powershell
python -m scripts.embed_knowledge_base_smoke_test
```

O `EmbeddingService` gera embeddings em lote, preserva a ordem das entradas,
valida índices, quantidade, dimensões e valores não finitos, e traduz falhas do
SDK para os erros internos da aplicação.

Esses comandos podem consumir créditos e não fazem parte do `pytest`. Os testes
automatizados usam cliente simulado e matemática vetorial local; eles não
acessam a OpenAI. Não existe RAG.

## Base de conhecimento

A base sintética está em:

```text
knowledge/articles.json
```

Cada artigo possui:

- identificador;
- título;
- conteúdo;
- categoria;
- palavras-chave.

Para validar e inspecionar:

```powershell
python -m scripts.inspect_knowledge_base
```

Os artigos são sintéticos e não contêm dados reais. A base possui 12 artigos,
com dois artigos para cada categoria de chamado. O ID técnico identifica o
artigo no arquivo, mas não entra no texto usado para embeddings. A representação
textual estável usa título, categoria, palavras-chave e conteúdo, nessa ordem.

Os embeddings persistentes dos artigos são criados somente pelo script explícito
de indexação no Chroma. O endpoint de busca exige essa indexação prévia e não
recalcula embeddings dos artigos por requisição. Ainda não existe resposta RAG.

## Recuperação semântica

A recuperação semântica atual usa uma base sintética de conhecimento,
embeddings, busca semântica top-k, endpoint interno, armazenamento persistente
local no Chroma e avaliação quantitativa da recuperação. O endpoint HTTP
consulta a coleção persistente; o índice em memória continua disponível para
scripts, testes e avaliações determinísticas.

```text
knowledge/articles.json
        |
        v
texto estável dos artigos
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

`KnowledgeVectorIndex` recebe os artigos e seus embeddings já calculados,
valida os vetores, calcula similaridade de cosseno, ordena os resultados por
maior pontuação e usa o ID do artigo como critério determinístico de desempate.
Ele permanece disponível para avaliação, testes e fallback explícito de
desenvolvimento.

No endpoint real, `ChromaKnowledgeSearchBackend` recebe apenas o embedding da
query, consulta a coleção Chroma com `query_embeddings`, converte distância de
cosseno em score e retorna `KnowledgeSearchMatch`. `KnowledgeSearchService`
depende apenas de um provedor assíncrono com `embed_text()` e de um backend de
busca, por isso a busca fica desacoplada do cliente concreto da OpenAI e do
mecanismo de armazenamento.

Comandos úteis:

```powershell
python -m scripts.inspect_knowledge_base
python -m scripts.search_knowledge_base_smoke_test
python -m scripts.evaluate_knowledge_retrieval
```

`scripts.inspect_knowledge_base` executa validações locais. Os scripts
`search_knowledge_base_smoke_test` e `evaluate_knowledge_retrieval` usam a API
real da OpenAI e podem consumir créditos.

As métricas de avaliação da recuperação são:

- Hit Rate@1, Hit Rate@3 e Hit Rate@5;
- Recall@1, Recall@3 e Recall@5;
- Mean Reciprocal Rank.

O baseline real e a análise estão documentados em
[`docs/evaluation.md`](docs/evaluation.md) e o fechamento técnico da semana está
em [`docs/week-3-review.md`](docs/week-3-review.md).

Não existe resposta RAG. A avaliação quantitativa da recuperação continua
independente do endpoint HTTP.

Para executar somente uma busca semântica real na base sintética:

```powershell
python -m scripts.search_knowledge_base_smoke_test
```

Esse comando usa a API real da OpenAI, pode consumir créditos e não faz parte do
`pytest`. Ele gera embeddings temporários, constrói o índice em memória e mostra
os resultados top-k para uma consulta sintética.

## Endpoint de busca semântica

```http
POST /internal/knowledge/search
```

O endpoint exige `X-API-Key`, recebe uma consulta e retorna os artigos mais
próximos semanticamente na coleção persistente do Chroma.

Requisição:

```json
{
  "query": "Redefini minha senha, mas ainda não consigo entrar",
  "top_k": 3,
  "category": "acesso_e_autenticacao"
}
```

Contrato:

- `query`: string normalizada com remoção de espaços externos, entre 3 e 1000
  caracteres;
- `top_k`: inteiro opcional entre 1 e 10, com padrão 3;
- `category`: categoria opcional para restringir a busca;
- campos extras são rejeitados.

Resposta:

- `query`: consulta normalizada;
- `model`: modelo de embeddings configurado;
- `indexed_articles`: quantidade de artigos na coleção persistente;
- `matches`: lista de resultados;
- `matches[].article`: artigo recuperado, com `id`, `title`, `content`,
  `category` e `keywords`;
- `matches[].score`: pontuação de similaridade de cosseno.

Os valores de `score` dependem dos embeddings gerados no momento da consulta. A
resposta não inclui uma resposta RAG final; ela apenas retorna os artigos
recuperados e suas pontuações.

Por requisição, o endpoint gera somente o embedding da query. Os embeddings dos
artigos são reaproveitados do Chroma e não são recalculados.

O filtro por categoria é representado por objeto de domínio e convertido
internamente para `where` do Chroma. Clientes HTTP não enviam sintaxe nativa do
Chroma e categorias inválidas são rejeitadas pela validação do schema.

### Endpoint de busca em lote

```http
POST /internal/knowledge/search/batch
```

Requisição:

```json
{
  "queries": [
    "não consigo entrar",
    "como exportar usuários?"
  ],
  "top_k": 3,
  "category": null
}
```

Resposta:

- `model`: modelo de embeddings configurado;
- `indexed_articles`: quantidade de artigos na coleção persistente;
- `results`: lista na mesma ordem das consultas;
- `results[].query`: consulta normalizada;
- `results[].matches`: resultados top-k daquela consulta.

O batch aceita de 1 a 20 consultas. O serviço gera embeddings das queries em
uma única chamada em lote e executa uma única operação `collection.query` com
`query_embeddings` contendo todos os vetores.

Erros documentados no OpenAPI:

- `401`: API Key interna ausente ou inválida;
- `422`: payload inválido;
- `502`: resposta inválida ou requisição rejeitada pelo provedor;
- `503`: provedor indisponível, sem configuração, sem conexão ou limitado;
- `504`: timeout do provedor.

## Avaliação da recuperação semântica

A avaliação da busca semântica usa um dataset sintético em:

```text
evaluation/knowledge_queries.json
```

O dataset contém 18 consultas sintéticas com julgamentos de relevância para os
artigos de `knowledge/articles.json`. Há casos com um artigo relevante e casos
com dois artigos relevantes, o que permite medir tanto presença de algum acerto
quanto recuperação parcial de múltiplos documentos.

As métricas calculadas são:

- Hit Rate@1, Hit Rate@3 e Hit Rate@5;
- Recall@1, Recall@3 e Recall@5;
- Mean Reciprocal Rank.

A avaliação é independente do endpoint HTTP. O script gera embeddings dos
artigos em lote, constrói o índice vetorial em memória e depois gera embeddings
das consultas em uma única chamada em lote. O MRR usa o ranking completo de cada
consulta, não apenas os resultados top-k.

Para executar a avaliação real:

```powershell
python -m scripts.evaluate_knowledge_retrieval
```

Esse comando usa a API real da OpenAI e pode consumir créditos. Ele não persiste
embeddings, não chama o endpoint HTTP e não gera resposta RAG.

## Semana 4 — Armazenamento vetorial

A busca semântica usa armazenamento vetorial persistente local no endpoint
HTTP. `KnowledgeSearchService` depende de um contrato de leitura,
`KnowledgeSearchBackend`, em vez de depender diretamente de uma implementação
concreta de índice.

`chromadb` está instalado e a integração com `PersistentClient` mantém uma
coleção local persistente. A indexação no Chroma é executada por script
separado; a aplicação abre a coleção existente no startup e falha de forma clara
quando a base ainda não foi indexada, está vazia ou possui metadata
incompatível.

Configuração atual:

- pacote `chromadb`;
- cliente `PersistentClient`;
- diretório `data/chroma`;
- coleção `helpdesklite-knowledge-v1`;
- distância de cosseno;
- função de embeddings do Chroma desabilitada;
- geração de vetores continua no `EmbeddingService`;
- endpoint `/internal/knowledge/search` consultando Chroma;
- estimativa local de tokens com `tiktoken`;
- custo estimado por configuração, sem chamada de billing.

Para inspecionar e validar a coleção persistente local:

```powershell
python -m scripts.inspect_chroma_collection
```

Esse comando cria ou obtém a coleção configurada, valida metadata e imprime a
quantidade de registros. Ele não gera embeddings, não indexa artigos e não
acessa a OpenAI.

Para estimar tokens/custo e indexar os 12 artigos reais no Chroma local:

```powershell
python -m scripts.index_knowledge_base
```

Esse comando usa a API real da OpenAI para gerar embeddings em lote. Antes da
chamada real, ele calcula uma estimativa determinística de tokens e custo. A
persistência usa `collection.upsert` com `KnowledgeArticle.id` como ID do
Chroma, portanto reexecutar o script atualiza os mesmos 12 registros sem criar
duplicatas.

### Busca semântica com armazenamento persistente

Antes de iniciar a API para busca real, a coleção precisa existir e conter os
artigos indexados:

```powershell
python -m scripts.index_knowledge_base
```

Fluxo do endpoint:

```text
Request HTTP
        |
        v
EmbeddingService
        |
        v
embedding da query
        |
        v
ChromaKnowledgeSearchBackend
        |
        v
coleção persistente
        |
        v
KnowledgeSearchMatch[]
```

Durante o startup, a aplicação abre a coleção existente com
`embedding_function=None`, valida schema, modelo de embedding e contagem maior
que zero. Durante cada request, somente a query é enviada ao provedor de
embeddings. Os embeddings dos artigos são reaproveitados do Chroma.

### Filtros de busca

A busca pode ser restringida por categoria usando os valores reais do enum do
projeto:

```json
{
  "query": "minha conta continua suspensa",
  "top_k": 3,
  "category": "cobranca"
}
```

O filtro é aplicado pelo Chroma antes da recuperação vetorial. A API não aceita
dicionários `where` arbitrários e não expõe operadores nativos do banco
vetorial.

### Busca em lote persistente

O endpoint batch usa o mesmo backend persistente:

```text
queries
        |
        v
EmbeddingService.embed_texts()
        |
        v
ChromaKnowledgeSearchBackend.search_many()
        |
        v
collection.query(query_embeddings=[...])
```

Para consulta manual em lote:

```powershell
python -m scripts.query_chroma_knowledge_batch `
  "não consigo acessar minha conta" `
  "como exportar usuários para CSV?" `
  --top-k 3
```

Filtro opcional:

```powershell
python -m scripts.query_chroma_knowledge_batch `
  "minha conta foi suspensa após pagamento" `
  --top-k 3 `
  --category cobranca
```

Esse script usa a API real da OpenAI para gerar embeddings das queries em lote.
Ele não imprime embeddings, documentos completos ou segredos.

### Consulta direta no Chroma

A coleção persistente pode ser consultada diretamente com embeddings externos.
`EmbeddingService` gera o vetor da consulta e `ChromaKnowledgeSearchBackend`
executa a busca na coleção. Como o Chroma retorna distância de cosseno, o backend
converte cada distância para similaridade com `score = 1 - distance`.

```powershell
python -m scripts.query_chroma_knowledge `
  "não consigo acessar minha conta" `
  --top-k 3
```

Esse comando usa a API real da OpenAI para gerar apenas o embedding da consulta.
Ele imprime ID, título, categoria e score, sem exibir embeddings, documentos
completos ou segredos.

O projeto também possui serviço de manutenção para atualização e remoção por ID
em coleções Chroma já configuradas. Atualizações verificam a existência do ID,
regeneram o embedding e usam `upsert` com o mesmo `KnowledgeArticle.id`.
Remoções verificam existência antes de chamar `delete`. Essas operações ainda
não são expostas no endpoint HTTP principal.

Decisão arquitetural:

```text
docs/decisions/0001-use-chroma-vector-store.md
```

Nesta etapa:

- Chroma foi instalado como dependência do projeto;
- a coleção local persistente pode ser criada pelo script de indexação;
- os 12 artigos podem ser indexados de forma idempotente por script separado;
- a coleção persistente pode ser consultada por backend Chroma desacoplado;
- o endpoint HTTP usa o backend Chroma inicializado no lifespan da aplicação;
- filtros por categoria são convertidos internamente para `where`;
- consultas em lote usam uma chamada de embeddings e uma chamada ao Chroma;
- atualização e remoção por ID existem como serviço interno;
- `data/chroma` é ignorado pelo Git;
- embeddings reais só são persistidos quando o script de indexação é executado;
- a busca em memória continua disponível para avaliação, testes e fallback
  explícito de desenvolvimento.

## Classificação de chamados

Entrada:

```json
{
  "title": "Não consigo acessar minha conta",
  "description": "Após redefinir minha senha, o sistema continua informando credenciais inválidas."
}
```

Resposta:

```json
{
  "category": "acesso_e_autenticacao",
  "priority": "alta",
  "summary": "Usuário permanece sem acesso após redefinir a senha.",
  "suggested_tags": [
    "login",
    "senha",
    "bloqueio"
  ],
  "model": "gpt-5-mini"
}
```

A resposta da OpenAI é validada com modelos Pydantic.

Não é realizado parsing manual de texto.

## Categorias

- `acesso_e_autenticacao`;
- `erro_tecnico`;
- `cobranca`;
- `duvida_de_uso`;
- `solicitacao`;
- `outro`.

## Prioridades

- `baixa`;
- `media`;
- `alta`;
- `critica`.

Critérios gerais:

- `baixa`: dúvida ou solicitação sem bloqueio;
- `media`: impacto limitado, com alternativa disponível;
- `alta`: usuário ou função importante bloqueada;
- `critica`: indisponibilidade ampla, risco de segurança ou perda de dados.

## Testar uma classificação diretamente

```powershell
python -m scripts.classify_ticket_smoke_test
```

Uma saída possível:

```text
Modelo: gpt-5-mini
{
  "category": "acesso_e_autenticacao",
  "priority": "alta",
  "summary": "Usuário permanece sem acesso após redefinir a senha.",
  "suggested_tags": [
    "login",
    "senha",
    "bloqueio"
  ]
}
```

Esse comando utiliza a API real e pode consumir créditos.

## Testar pelo Swagger UI

Abra:

```text
http://127.0.0.1:8000/docs
```

Depois:

1. clique em **Authorize**;
2. informe somente a `INTERNAL_API_KEY`;
3. abra `POST /internal/tickets/classify`;
4. clique em **Try it out**;
5. informe o chamado;
6. clique em **Execute**.

## Testar pelo PowerShell

Deixe o FastAPI em execução em outro terminal.

```powershell
$payload = @{
    title = "Não consigo acessar minha conta"
    description = "Depois de redefinir minha senha, o acesso continua bloqueado."
}

$jsonBody = $payload | ConvertTo-Json -Compress
$utf8Body = [System.Text.Encoding]::UTF8.GetBytes($jsonBody)
```

Configure a chamada:

```powershell
$headers = @{
    "X-API-Key" = "SUA_CHAVE_INTERNA"
}

$params = @{
    Method = "Post"
    Uri = "http://127.0.0.1:8000/internal/tickets/classify"
    Headers = $headers
    ContentType = "application/json; charset=utf-8"
    Body = $utf8Body
    TimeoutSec = 120
}
```

Execute:

```powershell
$response = Invoke-RestMethod @params
$response | ConvertTo-Json -Depth 5
```

A chamada final deve ser executada sem um backtick depois de `@params`.

## Respostas HTTP

| Código | Significado |
|---|---|
| `200` | Classificação concluída |
| `401` | API Key interna ausente ou inválida |
| `422` | Dados do chamado inválidos |
| `502` | Provedor retornou uma resposta inválida, incompleta ou recusou a operação |
| `503` | Provedor indisponível, limitado ou não configurado |
| `504` | Provedor excedeu o tempo limite |

## Contrato de erro

Falhas previsíveis utilizam:

```json
{
  "code": "ai_provider_timeout",
  "detail": "AI provider timed out.",
  "retryable": true
}
```

### Campos

- `code`: código estável da falha;
- `detail`: mensagem pública;
- `retryable`: informa se uma nova tentativa pode fazer sentido.

## Erros tratados

### Provedor não configurado

```json
{
  "code": "ai_provider_not_configured",
  "detail": "AI provider is not configured.",
  "retryable": false
}
```

Código HTTP:

```text
503 Service Unavailable
```

### Timeout

```json
{
  "code": "ai_provider_timeout",
  "detail": "AI provider timed out.",
  "retryable": true
}
```

Código HTTP:

```text
504 Gateway Timeout
```

### Falha de conexão

```json
{
  "code": "ai_provider_unreachable",
  "detail": "AI provider is temporarily unreachable.",
  "retryable": true
}
```

Código HTTP:

```text
503 Service Unavailable
```

### Rate limit

```json
{
  "code": "ai_provider_rate_limited",
  "detail": "AI provider rate limit was reached.",
  "retryable": true
}
```

A resposta também inclui:

```text
Retry-After: 30
```

### Resposta inválida

```json
{
  "code": "ai_provider_invalid_response",
  "detail": "AI provider returned an invalid response.",
  "retryable": false
}
```

Código HTTP:

```text
502 Bad Gateway
```

## Estratégias de prompt

### Zero-shot

Utiliza apenas regras e critérios, sem exemplos.

### One-shot

Utiliza um exemplo de chamado e classificação.

### Few-shot

Utiliza vários exemplos representando diferentes categorias e prioridades.

O one-shot é o baseline configurado atualmente. A comparação real mais recente
com 12 casos sintéticos deve ser acompanhada antes de promover mudanças de
baseline, porque pequenas alterações de prompt podem mudar o ranking entre
estratégias.

## Comparar estratégias

Primeiro, execute um teste econômico:

```powershell
python -m scripts.evaluate_ticket_classifier --strategy one_shot --limit 2
```

Depois, execute a avaliação completa do baseline:

```powershell
python -m scripts.evaluate_ticket_classifier --strategy one_shot
```

Para comparar todas as estratégias:

```powershell
python -m scripts.evaluate_ticket_classifier --all-strategies
```

O relatório é salvo em:

```text
reports/ticket-classification-evaluation.json
```

As métricas calculadas são:

- acurácia de categoria;
- acurácia de prioridade;
- acurácia conjunta, quando categoria e prioridade estão corretas no mesmo caso.

Resultado mais recente registrado em
`reports/ticket-classification-evaluation.json` com `gpt-5-mini` e 12 casos
sintéticos:

| Estratégia | Categoria | Prioridade | Conjunto |
|---|---:|---:|---:|
| `zero_shot` | 11/12, 91,67% | 12/12, 100% | 11/12, 91,67% |
| `one_shot` | 11/12, 91,67% | 12/12, 100% | 11/12, 91,67% |
| `few_shot` | 11/12, 91,67% | 12/12, 100% | 11/12, 91,67% |

As três estratégias empataram nessa execução. Como `one_shot` já é o baseline
configurado e `few_shot` tende a consumir mais tokens por incluir mais exemplos,
o baseline permanece `one_shot` até que um dataset maior sustente outra decisão.

O dataset ainda é pequeno e sintético. Ele serve para acompanhar regressões e
comparar mudanças de prompt, não como medida definitiva de qualidade em
produção.

Esses comandos usam a API real da OpenAI e podem consumir créditos. Os testes
automatizados usam classificadores falsos, mocks e respostas determinísticas;
eles não acessam a OpenAI.

Também existe um script de comparação qualitativa com um único chamado:

```powershell
python -m scripts.compare_prompt_strategies
```

O mesmo chamado será classificado com:

```text
Mesmo chamado
    |
    ├── Zero-shot
    ├── One-shot
    └── Few-shot
```

Compare:

- categoria;
- prioridade;
- fidelidade do resumo;
- relevância das tags;
- consistência;
- informações inventadas.

Esse comando realiza três requisições reais e pode consumir créditos.

## Qualidade do código

Execute:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\check.ps1
```

Ou individualmente:

```powershell
ruff check .
ruff format --check .
mypy app
pytest
```

Correção automática:

```powershell
ruff check . --fix
ruff format .
```

Os testes exigem cobertura mínima de 90%.

## Testes

Os testes verificam:

- disponibilidade e prontidão;
- autenticação interna;
- contrato OpenAPI;
- validação dos chamados;
- estratégias de prompt;
- saída estruturada;
- endpoint de classificação;
- falta de configuração;
- timeout;
- falha de conexão;
- rate limit;
- autenticação inválida do provedor;
- indisponibilidade;
- requisição rejeitada;
- resposta incompleta;
- recusa;
- resposta inválida;
- respostas HTTP padronizadas;
- header `Retry-After`;
- carregamento e validação da base de conhecimento;
- representação textual dos artigos;
- geração e validação de embeddings com cliente simulado;
- similaridade de cosseno;
- índice vetorial em memória;
- busca semântica com provedor falso.
- backend Chroma persistente com coleção temporária;
- endpoint de busca usando Chroma sem acessar OpenAI;
- garantia de que a request de busca embute somente a query.

Os testes:

- não usam uma chave real;
- não realizam chamadas externas;
- não consomem créditos;
- não carregam o `.env` local.

## Integração contínua

O GitHub Actions executa:

- lint com Ruff;
- verificação de formatação;
- análise estática com mypy;
- testes automatizados;
- validação da cobertura.

O workflow é executado em pushes e pull requests para `main`.

## Segurança

Nunca envie ao repositório:

- `.env`;
- chaves da OpenAI;
- chaves internas;
- arquivos de cobertura;
- ambiente virtual;
- caches.

O `.gitignore` deve incluir:

```gitignore
.env
.venv/
.coverage
coverage.xml
htmlcov/
__pycache__/
.pytest_cache/
.mypy_cache/
.ruff_cache/
```

O título e a descrição são tratados como dados não confiáveis.

O classificador é instruído a:

- não seguir comandos encontrados no chamado;
- analisar apenas o problema;
- não inventar urgência;
- respeitar os valores permitidos;
- retornar somente os campos do schema.

Caso uma chave seja exibida em uma captura, log ou commit, ela deve ser substituída imediatamente.

## Próximas funcionalidades

- geração de resposta RAG com artigos recuperados;
- integração com o backend do HelpDeskLite;
- logs estruturados;
- métricas e observabilidade;
- política de repetição e circuit breaker;
- deploy do serviço.
