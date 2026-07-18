# Arquitetura

## Visão geral

O AI Service é uma API independente construída com Python e FastAPI.

Inicialmente, ele será consumido pelo backend do HelpDeskLite. O serviço poderá ser reutilizado posteriormente por outras aplicações que precisem de funcionalidades de inteligência artificial.

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
Provedores e modelos de IA
```

## Camadas

### Application factory

O arquivo `app/main.py` cria a instância do FastAPI, carrega as configurações e registra as rotas.

Ele não deve conter regras de negócio ou implementações de endpoints.

### API

A pasta `app/api` contém a camada HTTP.

As rotas são responsáveis por:

- receber requisições;
- validar parâmetros por meio dos schemas;
- executar dependências;
- chamar serviços;
- transformar resultados em respostas HTTP.

As rotas não devem concentrar regras de negócio.

### Core

A pasta `app/core` contém recursos compartilhados pela aplicação, como:

- configurações;
- variáveis de ambiente;
- autenticação;
- segurança.

### Schemas

A pasta `app/schemas` contém modelos Pydantic que definem os contratos da API.

Os schemas determinam quais dados entram e saem dos endpoints.

### Services

A pasta `app/services` contém operações e regras da aplicação que não devem depender diretamente do protocolo HTTP.

Um serviço não deve conhecer objetos como `Request`, `Response` ou `APIRouter`.

### Tests

A pasta `tests` contém testes automatizados dos endpoints, serviços, configurações e contratos OpenAPI.

As configurações usadas nos testes são isoladas por meio das fixtures do pytest.

## Fluxo de uma requisição interna

```text
GET /internal/ping
        |
        v
APIKeyHeader lê X-API-Key
        |
        v
verify_api_key valida a chave
        |
        v
internal_ping executa
        |
        v
InternalPingResponse é retornado
```

## Regras de organização

1. Rotas lidam com HTTP.
2. Services concentram regras e operações da aplicação.
3. Schemas definem contratos de dados.
4. Configurações e segurança ficam em `core`.
5. Novas pastas somente devem ser criadas quando existir uma responsabilidade concreta.
6. Segredos nunca devem ser registrados no repositório.