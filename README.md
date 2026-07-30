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
- base de conhecimento sintética e versionada;
- validação de artigos com Pydantic;
- categorias e palavras-chave para artigos;
- representação textual estável para embeddings;
- cobertura mínima de testes;
- lint e formatação com Ruff;
- análise estática com mypy;
- integração contínua com GitHub Actions.

## Tecnologias

- Python 3.12
- FastAPI
- OpenAI Python SDK
- OpenAI Responses API
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
│   ├── knowledge/         # Carregamento e texto da base de conhecimento
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
OPENAI_PROMPT_STRATEGY=one_shot
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
OPENAI_PROMPT_STRATEGY=one_shot
```

O modelo pode ser alterado sem modificar o código-fonte.
`OPENAI_EMBEDDING_MODEL` define o modelo utilizado para gerar embeddings.

A variável `OPENAI_PROMPT_STRATEGY` define a estratégia de prompt. Os valores
permitidos são:

- `zero_shot`;
- `one_shot`;
- `few_shot`.

O baseline atual é `one_shot`.

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

Embeddings representam textos como vetores numéricos. A Semana 3 introduz a
base para busca semântica comparando esses vetores com similaridade de cosseno.
Ainda não há endpoint de busca, banco vetorial ou resposta final de um sistema
RAG.

Configure o `.env` e execute:

```powershell
python -m scripts.embedding_smoke_test
```

O smoke test envia textos sintéticos para a API real, usa o modelo definido em
`OPENAI_EMBEDDING_MODEL` e compara se dois textos sobre acesso/senha ficam mais
próximos entre si do que de um texto sobre alteração de plano.

Esse comando pode consumir créditos e não faz parte do `pytest`. Os testes
automatizados usam matemática vetorial local e mocks; eles não acessam a
OpenAI.

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

Os artigos são sintéticos e não contêm dados reais. O ID técnico identifica o
artigo no arquivo, mas não entra no texto usado para embeddings. A representação
textual estável usa título, categoria, palavras-chave e conteúdo, nessa ordem.

Nesta etapa, embeddings ainda não são armazenados. Também não existe banco
vetorial, endpoint de busca ou resposta RAG.

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
- header `Retry-After`.

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

- conjunto de avaliação com chamados conhecidos;
- cálculo de acurácia de categoria;
- cálculo de acurácia de prioridade;
- comparação quantitativa das estratégias;
- geração de embeddings para busca semântica;
- comparação vetorial por similaridade de cosseno;
- futura recuperação de artigos da base de conhecimento;
- integração com o backend do HelpDeskLite;
- logs estruturados;
- métricas e observabilidade;
- política de repetição e circuit breaker;
- deploy do serviço.
