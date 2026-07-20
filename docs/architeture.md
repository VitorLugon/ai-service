# Arquitetura

## Visão geral

O AI Service é uma API independente construída com Python e FastAPI para fornecer funcionalidades de inteligência artificial a aplicações internas.

O serviço será inicialmente consumido pelo backend do HelpDeskLite, mas sua arquitetura permite que outras aplicações também reutilizem suas funcionalidades.

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
Prompts e integrações de IA
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
│   │   ├── routes/
│   │   │   ├── health.py
│   │   │   ├── internal.py
│   │   │   └── readiness.py
│   │   └── router.py
│   ├── core/
│   │   ├── config.py
│   │   └── security.py
│   ├── prompts/
│   │   ├── __init__.py
│   │   └── ticket_classification.py
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
│   ├── __init__.py
│   ├── setup.ps1
│   ├── check.ps1
│   ├── dev.ps1
│   ├── openai_smoke_test.py
│   ├── classify_ticket_smoke_test.py
│   └── compare_prompt_strategies.py
├── tests/
│   ├── conftest.py
│   ├── test_health.py
│   ├── test_openapi.py
│   ├── test_readiness.py
│   ├── test_security.py
│   ├── test_ticket_classifier.py
│   └── test_ticket_classification_prompt.py
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
- carregar segredos do ambiente.

O arquivo `app/api/router.py` centraliza o registro dos routers.

### Core

A pasta `app/core` contém recursos compartilhados pela aplicação.

Atualmente, ela inclui:

- carregamento de variáveis de ambiente;
- configurações gerais do serviço;
- configurações da OpenAI API;
- autenticação interna por API Key;
- validação do header `X-API-Key`.

Segredos são carregados por variáveis de ambiente e não devem ser registrados no código, logs ou repositório.

### Prompts

A pasta `app/prompts` contém as instruções enviadas aos modelos de linguagem.

Os prompts permanecem separados dos services para permitir:

- comparação entre diferentes estratégias;
- testes do conteúdo estático;
- evolução das instruções sem alterar a integração com o provedor;
- reutilização em scripts e futuros endpoints;
- avaliação controlada de mudanças;
- versionamento independente das regras de prompting.

O classificador suporta atualmente três estratégias:

- `zero_shot`;
- `one_shot`;
- `few_shot`.

O arquivo `app/prompts/ticket_classification.py` contém:

- o enum `PromptStrategy`;
- as instruções básicas do classificador;
- os critérios de categoria;
- os critérios de prioridade;
- exemplos one-shot;
- exemplos few-shot;
- a função responsável por construir o prompt final.

O few-shot é utilizado como baseline inicial, mas não deve ser considerado automaticamente a melhor solução. A estratégia definitiva deverá ser escolhida a partir de avaliações com chamados representativos.

### Schemas

A pasta `app/schemas` contém modelos Pydantic que definem os contratos de entrada e saída da aplicação.

Atualmente, existem schemas para:

- saúde do serviço;
- prontidão;
- autenticação interna;
- entrada de chamados;
- resposta preliminar da classificação.

Os schemas de chamados validam:

- tamanho mínimo e máximo do título;
- tamanho mínimo e máximo da descrição;
- remoção de espaços desnecessários.

A resposta da classificação ainda é textual e armazenada como `TicketClassificationDraft`.

Uma etapa posterior substituirá esse contrato por uma resposta estruturada contendo campos validados para categoria, prioridade, resumo e tags.

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

A chave é armazenada como `SecretStr`.

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

O arquivo `app/services/ticket_classifier.py` contém o serviço responsável pela classificação inicial de chamados do HelpDeskLite.

O serviço recebe pelo construtor:

- cliente assíncrono da OpenAI;
- nome do modelo;
- estratégia de prompt.

Exemplo:

```python
classifier = TicketClassifierService(
    client=client,
    model="gpt-5-mini",
    prompt_strategy=PromptStrategy.FEW_SHOT,
)
```

O service não:

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
PromptStrategy
        |
        v
build_ticket_classification_instructions
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

## Estratégias de prompting

### Zero-shot

A estratégia zero-shot utiliza somente:

- identidade do classificador;
- instruções da tarefa;
- categorias permitidas;
- prioridades permitidas;
- critérios de prioridade;
- formato esperado da resposta.

Nenhum exemplo de entrada e saída é fornecido ao modelo.

### One-shot

A estratégia one-shot adiciona um exemplo completo de classificação.

O objetivo é demonstrar:

- formato esperado;
- estilo do resumo;
- uso de tags;
- relacionamento entre um problema e sua classificação.

### Few-shot

A estratégia few-shot adiciona vários exemplos de chamados diferentes.

Os exemplos atuais representam:

- cobrança duplicada;
- bloqueio de acesso;
- indisponibilidade geral do sistema.

Isso ajuda o modelo a observar diferentes níveis de impacto e prioridade.

O few-shot é o baseline padrão atual do `TicketClassifierService`.

## Comparação entre estratégias

O script `scripts/compare_prompt_strategies.py` executa o mesmo chamado utilizando:

```text
zero_shot
one_shot
few_shot
```

O fluxo é:

```text
Chamado de avaliação
        |
        ├── Zero-shot
        ├── One-shot
        └── Few-shot
                |
                v
Resultados exibidos no terminal
```

Os resultados são comparados qualitativamente considerando:

- formato correto;
- categoria válida;
- prioridade coerente;
- resumo objetivo;
- tags relevantes;
- ausência de texto extra.

A execução realiza três requisições reais e pode consumir créditos da API.

## Tratamento do conteúdo recebido

O título e a descrição de um chamado são considerados dados não confiáveis.

As instruções enviadas ao modelo determinam que comandos encontrados no conteúdo do chamado não devem ser executados ou seguidos.

O chamado é serializado como JSON para melhorar a separação entre:

- instruções do sistema;
- conteúdo fornecido pelo usuário.

Essa separação reduz ambiguidades, mas não elimina completamente riscos relacionados a prompt injection.

Outras validações serão adicionadas posteriormente.

## Scripts

A pasta `scripts` contém operações de desenvolvimento, validação e testes manuais.

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

### `compare_prompt_strategies.py`

Classifica o mesmo chamado usando zero-shot, one-shot e few-shot.

Os scripts que acessam a OpenAI API utilizam a API real e podem consumir créditos.

## Testes

A pasta `tests` contém testes automatizados dos endpoints, services, configurações, prompts e contratos OpenAPI.

As configurações usadas nos testes são isoladas por meio de fixtures do pytest.

A integração com a OpenAI é simulada utilizando:

- `MagicMock`;
- `AsyncMock`;
- respostas simuladas.

Os testes automatizados não devem realizar requisições reais nem consumir créditos.

Os testes do classificador verificam:

- retorno do texto produzido pelo modelo;
- envio dos parâmetros corretos ao SDK;
- rejeição de respostas vazias;
- validação dos dados de entrada;
- serialização do chamado;
- utilização da estratégia selecionada.

Os testes dos prompts verificam:

- ausência de exemplos no zero-shot;
- presença de um exemplo no one-shot;
- presença de vários exemplos no few-shot;
- categorias permitidas;
- prioridades permitidas;
- manutenção do contrato estático das instruções.

Esses testes não avaliam a qualidade das respostas do modelo. Avaliações de qualidade serão adicionadas posteriormente usando um conjunto representativo de chamados.

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
4. Prompts ficam separados dos services.
5. Configurações e segurança ficam em `core`.
6. Clientes externos devem ser recebidos como dependências.
7. Chamados e outros conteúdos de usuários são dados não confiáveis.
8. Testes automatizados não devem consumir APIs externas.
9. Novas pastas somente devem ser criadas quando existir uma responsabilidade concreta.
10. Segredos nunca devem ser registrados no repositório.
11. Funcionalidades de IA devem ser implementadas primeiro como services e depois expostas por endpoints.
12. Mudanças em prompts devem ser acompanhadas por testes e avaliações.