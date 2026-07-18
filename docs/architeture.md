# Arquitetura

## Visão geral

O AI Service é uma API independente construída com Python e FastAPI para fornecer funcionalidades de inteligência artificial a aplicações internas.

Inicialmente, o serviço será consumido pelo backend do HelpDeskLite. Sua arquitetura permite que outras aplicações também utilizem suas funcionalidades futuramente.

```text
HelpDeskLite Backend
        |
        | HTTP + X-API-Key
        v
AI Service — FastAPI
        |
        v
Serviços de aplicação
        |
        v
OpenAI API e outros provedores de IA
```

## Estrutura do projeto

```text
ai-service/
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── health.py
│   │   │   ├── internal.py
│   │   │   └── readiness.py
│   │   └── router.py
│   ├── core/
│   │   ├── config.py
│   │   └── security.py
│   ├── schemas/
│   │   ├── health.py
│   │   ├── internal.py
│   │   ├── readiness.py
│   │   └── tickets.py
│   ├── services/
│   │   ├── readiness.py
│   │   └── ticket_classifier.py
│   └── main.py
├── docs/
│   └── architecture.md
├── scripts/
│   ├── setup.ps1
│   ├── check.ps1
│   ├── dev.ps1
│   ├── openai_smoke_test.py
│   └── classify_ticket_smoke_test.py
├── tests/
├── .env.example
├── .python-version
├── pyproject.toml
└── requirements.txt
```

## Camadas

### Application factory

O arquivo `app/main.py` cria e configura a aplicação FastAPI.

Suas responsabilidades são:

- carregar as configurações;
- criar a instância do FastAPI;
- registrar os routers;
- disponibilizar a aplicação para execução.

Esse arquivo não deve conter regras de negócio ou implementações de endpoints.

### API

A pasta `app/api` representa a camada HTTP da aplicação.

As rotas são responsáveis por:

- receber requisições;
- validar dados por meio dos schemas;
- executar dependências;
- chamar serviços;
- transformar resultados em respostas HTTP.

As rotas não devem concentrar regras de negócio ou criar diretamente prompts complexos.

O arquivo `app/api/router.py` centraliza o registro dos routers.

### Core

A pasta `app/core` contém recursos compartilhados pela aplicação.

Atualmente, ela inclui:

- carregamento de variáveis de ambiente;
- configurações gerais do serviço;
- configuração da OpenAI API;
- autenticação interna por API Key;
- validação do header `X-API-Key`.

Segredos são carregados por variáveis de ambiente e não devem ser registrados no código ou no repositório.

### Schemas

A pasta `app/schemas` contém os modelos Pydantic que definem os contratos de entrada e saída da aplicação.

Atualmente, existem schemas para:

- saúde do serviço;
- prontidão;
- autenticação interna;
- entrada de chamados;
- resposta preliminar da classificação.

Os schemas de chamados validam informações como:

- tamanho mínimo e máximo do título;
- tamanho mínimo e máximo da descrição;
- remoção de espaços desnecessários.

### Services

A pasta `app/services` contém operações e regras da aplicação que não dependem diretamente do protocolo HTTP.

Um service não deve conhecer objetos como:

- `Request`;
- `Response`;
- `APIRouter`;
- headers HTTP.

As dependências necessárias são recebidas explicitamente pelo construtor ou pelos métodos.

## Verificação de prontidão

O arquivo `app/services/readiness.py` contém o serviço responsável por verificar se a aplicação está preparada para receber tráfego.

O fluxo atual é:

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

- acesso ao provedor de IA;
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

A configuração da OpenAI é carregada por meio das variáveis:

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5-mini
```

A chave é armazenada como `SecretStr` e não deve ser exibida em logs ou mensagens de erro.

A aplicação utiliza o cliente assíncrono `AsyncOpenAI`, compatível com o fluxo assíncrono do FastAPI.

O script `scripts/openai_smoke_test.py` realiza uma requisição mínima para validar a comunicação:

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

## Classificação de chamados

O arquivo `app/services/ticket_classifier.py` contém a integração inicial responsável por classificar chamados do HelpDeskLite.

O serviço recebe pelo construtor:

- cliente da OpenAI;
- nome do modelo.

Ele não:

- carrega diretamente o arquivo `.env`;
- procura a API Key;
- cria sozinho o cliente da OpenAI;
- depende do FastAPI;
- conhece detalhes da camada HTTP.

O fluxo atual é:

```text
TicketClassificationInput
        |
        v
TicketClassifierService
        |
        v
Serialização do chamado como JSON
        |
        v
OpenAI Responses API
        |
        v
TicketClassificationDraft
```

A entrada contém:

```json
{
  "title": "Não consigo acessar minha conta",
  "description": "Após redefinir minha senha, o sistema informa credenciais inválidas."
}
```

A classificação textual inicial segue o formato:

```text
Categoria: acesso_e_autenticacao
Prioridade: alta
Resumo: Usuário não consegue acessar a conta após redefinir a senha.
Tags: login, senha
```

As categorias disponíveis atualmente são:

```text
acesso_e_autenticacao
erro_tecnico
cobranca
duvida_de_uso
solicitacao
outro
```

As prioridades disponíveis são:

```text
baixa
media
alta
critica
```

A resposta ainda é textual e armazenada em `TicketClassificationDraft`.

Uma etapa posterior substituirá esse formato por uma saída estruturada e validada pelo Pydantic.

## Tratamento do conteúdo recebido

O título e a descrição de um chamado são considerados dados não confiáveis.

As instruções enviadas ao modelo determinam que comandos encontrados no conteúdo do chamado não devem ser executados ou seguidos.

O chamado é serializado como JSON para melhorar a separação entre:

- instruções do sistema;
- conteúdo fornecido pelo usuário.

Essa separação reduz ambiguidades, mas não elimina completamente riscos relacionados a prompt injection. Outras validações serão adicionadas posteriormente.

## Scripts

A pasta `scripts` contém operações de desenvolvimento e validação.

### `setup.ps1`

Responsável por:

- criar o ambiente virtual;
- instalar dependências;
- atualizar o pip;
- criar o `.env` a partir do `.env.example`.

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

Realiza uma requisição mínima para verificar a conexão com a OpenAI API.

### `classify_ticket_smoke_test.py`

Envia um chamado de exemplo para o `TicketClassifierService` e exibe a classificação retornada pelo modelo.

Os smoke tests utilizam a API real e podem consumir créditos.

## Testes

A pasta `tests` contém testes automatizados dos endpoints, serviços, configurações e contratos OpenAPI.

As configurações usadas nos testes são isoladas por meio de fixtures do pytest.

A integração com a OpenAI é testada utilizando:

- `MagicMock`;
- `AsyncMock`;
- respostas simuladas.

Os testes automatizados não devem realizar requisições reais nem consumir créditos.

Os testes do classificador verificam:

- retorno do texto produzido pelo modelo;
- envio dos parâmetros corretos ao SDK;
- rejeição de respostas vazias;
- validação dos dados de entrada;
- serialização do chamado.

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
2. Services concentram operações e regras da aplicação.
3. Schemas definem contratos de entrada e saída.
4. Configurações e segurança ficam em `core`.
5. Clientes externos devem ser recebidos como dependências.
6. Chamados e outros conteúdos de usuários são dados não confiáveis.
7. Testes automatizados não devem consumir APIs externas.
8. Novas pastas somente devem ser criadas quando existir uma responsabilidade concreta.
9. Segredos nunca devem ser registrados no repositório.
10. Funcionalidades de IA devem ser implementadas primeiro como services e depois expostas por endpoints.