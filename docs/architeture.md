# Arquitetura

## Visão geral

O AI Service é uma API independente construída com Python e FastAPI para fornecer funcionalidades de inteligência artificial a aplicações internas.

O serviço será inicialmente consumido pelo backend do HelpDeskLite, mas sua arquitetura permite que outras aplicações reutilizem suas funcionalidades.

```text
HelpDeskLite Backend
        |
        | HTTP + X-API-Key
        v
AI Service — FastAPI
        |
        v
Rotas e dependências
        |
        v
Serviços de aplicação
        |
        v
Prompts e contratos Pydantic
        |
        v
OpenAI Responses API
```

## Estrutura do projeto

```text
ai-service/
├── .github/
│   └── workflows/
│       └── ci.yml
├── app/
│   ├── api/
│   │   ├── dependencies/
│   │   │   ├── __init__.py
│   │   │   └── ticket_classifier.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── health.py
│   │   │   ├── internal.py
│   │   │   ├── readiness.py
│   │   │   └── tickets.py
│   │   ├── __init__.py
│   │   ├── exception_handlers.py
│   │   └── router.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── exceptions.py
│   │   └── security.py
│   ├── prompts/
│   │   ├── __init__.py
│   │   └── ticket_classification.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── errors.py
│   │   ├── health.py
│   │   ├── internal.py
│   │   ├── readiness.py
│   │   └── tickets.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── readiness.py
│   │   └── ticket_classifier.py
│   ├── __init__.py
│   └── main.py
├── docs/
│   └── architecture.md
├── scripts/
│   ├── __init__.py
│   ├── setup.ps1
│   ├── check.ps1
│   ├── dev.ps1
│   ├── openai_smoke_test.py
│   ├── classify_ticket_smoke_test.py
│   └── compare_prompt_strategies.py
├── tests/
│   ├── conftest.py
│   ├── test_ai_provider_error_api.py
│   ├── test_health.py
│   ├── test_openapi.py
│   ├── test_readiness.py
│   ├── test_security.py
│   ├── test_ticket_classification_api.py
│   ├── test_ticket_classification_prompt.py
│   ├── test_ticket_classifier.py
│   └── test_ticket_classifier_errors.py
├── .env.example
├── .gitignore
├── .python-version
├── pyproject.toml
├── README.md
└── requirements.txt
```

## Camadas

### Application factory

O arquivo `app/main.py` cria e configura a aplicação FastAPI.

Suas responsabilidades são:

- carregar as configurações;
- criar a instância do FastAPI;
- registrar os routers;
- registrar os handlers globais de exceção;
- disponibilizar a aplicação para execução.

Esse arquivo não deve conter regras de negócio, prompts ou implementações de endpoints.

### API

A pasta `app/api` representa a camada HTTP da aplicação.

As rotas são responsáveis por:

- receber requisições;
- validar dados por meio dos schemas;
- executar dependências;
- chamar services;
- transformar resultados em respostas HTTP.

As rotas não devem:

- concentrar regras de negócio;
- construir prompts extensos;
- criar diretamente clientes de APIs externas;
- carregar segredos do ambiente;
- tratar individualmente todas as exceções do provedor.

O arquivo `app/api/router.py` centraliza o registro dos routers.

### Dependencies

A pasta `app/api/dependencies` contém dependências utilizadas pelo FastAPI.

O arquivo `ticket_classifier.py` é responsável por:

- carregar as configurações necessárias;
- verificar se a OpenAI API está configurada;
- criar o cliente assíncrono da OpenAI;
- criar o `TicketClassifierService`;
- encerrar o cliente depois da requisição.

A chave da OpenAI permanece no ambiente do AI Service e não é recebida do cliente HTTP.

### Exception handlers

O arquivo `app/api/exception_handlers.py` converte exceções da aplicação em respostas HTTP padronizadas.

O handler global é registrado no momento da criação da aplicação.

Esse módulo é responsável por:

- escolher o código HTTP adequado;
- gerar uma resposta segura;
- informar se a falha permite nova tentativa;
- adicionar headers específicos, como `Retry-After`.

Os handlers não retornam detalhes internos do SDK ou informações sensíveis.

### Core

A pasta `app/core` contém recursos compartilhados pela aplicação.

Atualmente, ela inclui:

- carregamento de variáveis de ambiente;
- configurações gerais do serviço;
- configurações da OpenAI API;
- autenticação interna por API Key;
- exceções próprias da aplicação;
- validação do header `X-API-Key`.

Segredos são carregados por variáveis de ambiente e não devem ser registrados no código, nos logs ou no repositório.

### Prompts

A pasta `app/prompts` contém as instruções enviadas aos modelos de linguagem.

Os prompts permanecem separados dos services para permitir:

- comparação entre estratégias;
- testes do conteúdo estático;
- evolução das instruções sem modificar a integração;
- reutilização em scripts e endpoints;
- avaliação controlada de mudanças.

O classificador suporta atualmente:

- `zero_shot`;
- `one_shot`;
- `few_shot`.

O arquivo `ticket_classification.py` contém:

- o enum `PromptStrategy`;
- as instruções principais;
- os critérios de categoria;
- os critérios de prioridade;
- os exemplos one-shot;
- os exemplos few-shot;
- a função que constrói o prompt final.

O few-shot é utilizado como baseline inicial. A estratégia definitiva deverá ser escolhida a partir de avaliações com chamados representativos.

### Schemas

A pasta `app/schemas` contém modelos Pydantic que definem os contratos da aplicação.

Atualmente, existem schemas para:

- saúde do serviço;
- prontidão;
- autenticação interna;
- entrada de chamados;
- classificação estruturada;
- resposta HTTP da classificação;
- erros previsíveis da aplicação.

Os schemas de chamados validam:

- tamanho mínimo e máximo do título;
- tamanho mínimo e máximo da descrição;
- remoção de espaços desnecessários;
- categorias permitidas;
- prioridades permitidas;
- tamanho do resumo;
- quantidade e tamanho das tags;
- rejeição de campos adicionais inesperados.

### Services

A pasta `app/services` contém operações e regras que não dependem diretamente do protocolo HTTP.

Um service não deve conhecer objetos como:

- `Request`;
- `Response`;
- `APIRouter`;
- headers HTTP.

As dependências externas necessárias são recebidas pelo construtor.

## Verificação de prontidão

O arquivo `app/services/readiness.py` verifica se a aplicação está preparada para receber tráfego.

```text
GET /ready
        |
        v
ReadinessService
        |
        v
Verificação das configurações
        |
        v
200 Ready ou 503 Not Ready
```

Novas verificações poderão ser adicionadas posteriormente, como:

- conexão com banco de dados;
- disponibilidade do Redis;
- carregamento de modelos;
- acesso a armazenamento vetorial.

## Autenticação interna

Os endpoints internos utilizam uma API Key enviada no header:

```text
X-API-Key: chave-interna
```

O fluxo de autenticação é:

```text
Requisição interna
        |
        v
APIKeyHeader lê X-API-Key
        |
        v
verify_api_key compara a chave recebida
        |
        v
Endpoint interno é executado
```

A comparação é realizada com `secrets.compare_digest`.

As rotas `/health` e `/ready` permanecem públicas.

## Integração com a OpenAI API

A configuração da OpenAI é carregada pelas variáveis:

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5-mini
```

A chave é armazenada como `SecretStr`.

A aplicação utiliza `AsyncOpenAI`, permitindo que as requisições externas sejam aguardadas de maneira assíncrona.

O script `scripts/openai_smoke_test.py` realiza uma requisição mínima:

```text
AI Service
        |
        v
OpenAI Python SDK
        |
        v
OpenAI Responses API
        |
        v
Resposta do modelo
```

## Classificação estruturada de chamados

O arquivo `app/services/ticket_classifier.py` contém o serviço responsável pela classificação de chamados.

O serviço recebe pelo construtor:

- cliente assíncrono da OpenAI;
- nome do modelo;
- estratégia de prompt.

```python
classifier = TicketClassifierService(
    client=client,
    model="gpt-5-mini",
    prompt_strategy=PromptStrategy.FEW_SHOT,
)
```

O service não:

- carrega diretamente o `.env`;
- procura a API Key;
- cria sozinho o cliente da OpenAI;
- depende do FastAPI;
- conhece detalhes da camada HTTP.

O fluxo é:

```text
TicketClassificationInput
        |
        v
PromptStrategy
        |
        v
Prompt de classificação
        |
        v
TicketClassifierService
        |
        v
OpenAI Responses API
        |
        v
Structured Output
        |
        v
TicketClassificationResult
```

A entrada contém:

```json
{
  "title": "Não consigo acessar minha conta",
  "description": "Após redefinir minha senha, o sistema informa credenciais inválidas."
}
```

A resposta estruturada contém:

```json
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

A aplicação utiliza `responses.parse()` com um modelo Pydantic.

Não é necessário realizar parsing manual de texto.

## Categorias e prioridades

As categorias permitidas são:

```text
acesso_e_autenticacao
erro_tecnico
cobranca
duvida_de_uso
solicitacao
outro
```

As prioridades permitidas são:

```text
baixa
media
alta
critica
```

Enums impedem que valores fora das listas sejam aceitos pelo contrato da aplicação.

## Estratégias de prompting

### Zero-shot

Utiliza apenas:

- identidade;
- regras;
- categorias;
- prioridades;
- critérios de impacto.

Nenhum exemplo é fornecido.

### One-shot

Inclui uma classificação completa de exemplo.

### Few-shot

Inclui vários exemplos representando:

- cobrança duplicada;
- bloqueio de acesso;
- indisponibilidade ampla.

O few-shot é o baseline atual do classificador.

## Endpoint de classificação

O endpoint disponível é:

```text
POST /internal/tickets/classify
```

O fluxo completo é:

```text
Requisição HTTP
        |
        v
Validação da X-API-Key
        |
        v
TicketClassificationInput
        |
        v
get_ticket_classifier
        |
        v
TicketClassifierService
        |
        v
OpenAI Responses API
        |
        v
TicketClassificationResponse
```

A rota permanece fina e não contém detalhes do prompt ou do SDK.

## Tratamento de conteúdo não confiável

O título e a descrição são considerados dados não confiáveis.

As instruções determinam que o modelo deve:

- não executar comandos presentes no chamado;
- não seguir instruções encontradas na descrição;
- analisar apenas o problema relatado;
- não inventar impacto ou urgência;
- utilizar somente os valores permitidos pelo contrato.

O chamado é serializado como JSON antes do envio ao modelo.

Essa separação reduz ambiguidades, mas não elimina completamente riscos relacionados a prompt injection.

## Tratamento de erros do provedor

O `TicketClassifierService` converte exceções do SDK da OpenAI em exceções próprias da aplicação.

```text
OpenAI SDK error
        |
        v
TicketClassifierService
        |
        v
AIProviderError
        |
        v
Global exception handler
        |
        v
Resposta HTTP padronizada
```

As principais exceções são:

- `AIProviderConfigurationError`;
- `AIProviderTimeoutError`;
- `AIProviderConnectionError`;
- `AIProviderRateLimitError`;
- `AIProviderUnavailableError`;
- `AIProviderRequestError`;
- `AIProviderIncompleteResponseError`;
- `AIProviderRefusalError`;
- `AIProviderInvalidResponseError`.

O service não cria respostas HTTP.

O módulo `app/api/exception_handlers.py` realiza o mapeamento:

| Exceção | Código HTTP |
|---|---:|
| Configuração inválida | `503` |
| Timeout | `504` |
| Falha de conexão | `503` |
| Rate limit do provedor | `503` |
| Indisponibilidade do provedor | `503` |
| Requisição rejeitada | `502` |
| Resposta incompleta | `502` |
| Recusa | `502` |
| Resposta inválida | `502` |

O rate limit inclui:

```text
Retry-After: 30
```

As mensagens originais do SDK não são retornadas ao cliente.

## Contrato de erros

Falhas previsíveis utilizam o schema:

```json
{
  "code": "ai_provider_timeout",
  "detail": "AI provider timed out.",
  "retryable": true
}
```

Os campos representam:

- `code`: identificador estável da falha;
- `detail`: mensagem pública e segura;
- `retryable`: indica se uma nova tentativa pode fazer sentido.

## Scripts

### `setup.ps1`

Responsável por:

- criar o ambiente virtual;
- instalar dependências;
- atualizar o pip;
- criar o `.env` quando necessário.

### `dev.ps1`

Inicializa a aplicação FastAPI em modo de desenvolvimento.

### `check.ps1`

Executa:

- Ruff;
- verificação de formatação;
- mypy;
- pytest;
- cobertura de testes.

### `openai_smoke_test.py`

Valida a conexão com a OpenAI API.

### `classify_ticket_smoke_test.py`

Executa uma classificação estruturada usando a API real.

### `compare_prompt_strategies.py`

Classifica o mesmo chamado usando zero-shot, one-shot e few-shot.

Os scripts que acessam a OpenAI utilizam a API real e podem consumir créditos.

## Testes

Os testes automatizados utilizam fixtures, mocks e configurações isoladas.

A integração com a OpenAI é simulada com:

- `MagicMock`;
- `AsyncMock`;
- exceções construídas localmente;
- respostas simuladas.

Os testes verificam:

- saúde e prontidão;
- autenticação interna;
- contrato OpenAPI;
- validação dos chamados;
- prompts zero-shot, one-shot e few-shot;
- saída estruturada;
- endpoint de classificação;
- ausência de configuração da OpenAI;
- timeout;
- falha de conexão;
- rate limit;
- autenticação inválida do provedor;
- erro interno do provedor;
- requisição rejeitada;
- resposta incompleta;
- recusa;
- resposta estruturada inválida;
- mapeamento para códigos HTTP;
- header `Retry-After`.

Os testes automatizados:

- não usam uma chave real;
- não realizam chamadas externas;
- não consomem créditos;
- não carregam o `.env` local.

## Integração contínua

O GitHub Actions executa automaticamente:

- lint com Ruff;
- verificação de formatação;
- análise de tipos com mypy;
- testes automatizados;
- validação da cobertura mínima.

O workflow é executado em pushes e pull requests para a branch `main`.

## Regras de organização

1. Rotas lidam com HTTP.
2. Services concentram operações e regras.
3. Schemas definem contratos.
4. Prompts ficam separados dos services.
5. Configurações, segurança e exceções ficam em `core`.
6. Dependências externas são construídas pela camada de dependencies.
7. Handlers globais convertem exceções em respostas HTTP.
8. Clientes externos são recebidos por injeção de dependência.
9. Conteúdos fornecidos por usuários são considerados não confiáveis.
10. Testes automatizados não devem consumir APIs externas.
11. Segredos nunca devem ser registrados no repositório.
12. Mudanças em prompts devem ser acompanhadas por testes e avaliações.
13. Mensagens internas do provedor não devem ser expostas aos clientes.