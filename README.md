# AI Service

API independente construída com Python e FastAPI para fornecer funcionalidades de inteligência artificial a aplicações internas.

O serviço será inicialmente integrado ao HelpDeskLite e poderá ser reutilizado por outros projetos.

## Funcionalidades atuais

- endpoint de saúde da aplicação;
- endpoint de prontidão;
- configuração por variáveis de ambiente;
- autenticação interna por API Key;
- integração inicial com a OpenAI API;
- script de validação da conexão com o modelo;
- documentação automática com OpenAPI e Swagger UI;
- testes automatizados;
- cobertura mínima de testes;
- lint e formatação com Ruff;
- análise estática com mypy;
- integração contínua com GitHub Actions.

## Tecnologias

- Python 3.12
- FastAPI
- OpenAI Python SDK
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
│   ├── api/          # Rotas e configuração HTTP
│   ├── core/         # Configurações e segurança
│   ├── schemas/      # Contratos Pydantic
│   ├── services/     # Operações e regras da aplicação
│   └── main.py       # Criação da aplicação FastAPI
├── docs/             # Documentação da arquitetura
├── scripts/          # Instalação, execução e validações
└── tests/            # Testes automatizados
```

A descrição completa está em [`docs/architecture.md`](docs/architecture.md).

## Requisitos

- Python 3.12
- Git
- PowerShell
- chave da OpenAI API para executar funcionalidades de inteligência artificial

As rotas básicas, como `/health` e `/ready`, funcionam sem uma chave da OpenAI.

## Instalação no Windows

Clone o repositório:

```powershell
git clone https://github.com/VitorLugon/ai-service.git
cd ai-service
```

Execute o script de instalação:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
```

O script:

- cria o ambiente virtual;
- atualiza o pip;
- instala as dependências;
- cria o `.env` a partir do `.env.example`, quando necessário.

## Variáveis de ambiente

As configurações locais devem ser armazenadas no arquivo `.env`.

Exemplo:

```env
APP_NAME=AI Service
APP_VERSION=0.1.0
ENVIRONMENT=development

INTERNAL_API_KEY=sua-chave-interna

OPENAI_API_KEY=sua-chave-da-openai
OPENAI_MODEL=gpt-5-mini
```

### Chave interna

A variável `INTERNAL_API_KEY` protege a comunicação entre o AI Service e aplicações internas, como o backend do HelpDeskLite.

Uma chave aleatória pode ser gerada com:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### OpenAI API

A variável `OPENAI_API_KEY` deve receber uma chave válida da OpenAI API.

A variável `OPENAI_MODEL` determina qual modelo será utilizado pelo serviço:

```env
OPENAI_API_KEY=sk-proj-sua-chave
OPENAI_MODEL=gpt-5-mini
```

O modelo pode ser alterado por configuração sem modificar o código-fonte.

Nunca coloque uma chave real no `.env.example`, no README ou diretamente no código.

## Executar localmente

Execute:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev.ps1
```

A aplicação será disponibilizada em:

```text
http://127.0.0.1:8000
```

A documentação interativa estará em:

```text
http://127.0.0.1:8000/docs
```

A documentação alternativa estará em:

```text
http://127.0.0.1:8000/redoc
```

## Endpoints

| Método | Endpoint | Autenticação | Descrição |
|---|---|---|---|
| GET | `/health` | Não | Verifica se o processo da aplicação está funcionando |
| GET | `/ready` | Não | Verifica se o serviço está pronto para receber requisições |
| GET | `/internal/ping` | API Key | Valida a autenticação entre serviços internos |

## Autenticação interna

Os endpoints internos exigem uma API Key enviada pelo header:

```text
X-API-Key: sua-chave
```

Exemplo no PowerShell:

```powershell
curl.exe `
  -H "X-API-Key: SUA_CHAVE" `
  http://127.0.0.1:8000/internal/ping
```

Resposta esperada:

```json
{
  "status": "ok",
  "message": "Internal authentication succeeded."
}
```

As rotas `/health` e `/ready` são públicas.

## Testar a integração com a OpenAI

Depois de configurar `OPENAI_API_KEY` e `OPENAI_MODEL` no `.env`, execute:

```powershell
python -m scripts.openai_smoke_test
```

Resultado esperado:

```text
Modelo: gpt-5-mini
Resposta: ok
```

Esse script realiza uma requisição mínima para confirmar o fluxo:

```text
AI Service
    |
    v
OpenAI Python SDK
    |
    v
OpenAI API
    |
    v
Resposta do modelo
```

O teste pode consumir uma pequena quantidade dos créditos disponíveis na conta da API.

## Qualidade do código

Execute todas as verificações com:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\check.ps1
```

Também é possível executar cada comando separadamente:

```powershell
ruff check .
ruff format --check .
mypy app
pytest
```

Para corrigir automaticamente problemas seguros de lint e formatação:

```powershell
ruff check . --fix
ruff format .
```

Os testes exigem cobertura mínima de 90%.

## Testes

Os testes automatizados verificam atualmente:

- disponibilidade da aplicação;
- prontidão do serviço;
- autenticação por API Key;
- respostas para chaves ausentes ou inválidas;
- contrato OpenAPI;
- esquema de segurança exibido na documentação.

Os testes não utilizam uma chave real da OpenAI e não devem consumir créditos da API.

## Integração contínua

O GitHub Actions executa automaticamente:

- lint com Ruff;
- verificação de formatação;
- análise estática de tipos;
- testes automatizados;
- validação da cobertura mínima.

O workflow é executado em pushes e pull requests para a branch `main`.

## Segurança

Os seguintes arquivos e dados nunca devem ser enviados ao repositório:

- `.env`;
- chaves da OpenAI API;
- chaves internas reais;
- arquivos de cobertura;
- ambiente virtual;
- caches das ferramentas.

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

## Próximas funcionalidades

- classificação automática de chamados;
- definição estruturada de categoria e prioridade;
- geração de resumos de chamados;
- sugestão automática de tags;
- tratamento estruturado de erros da OpenAI API;
- mocks para testar integrações sem consumir créditos;
- observabilidade e logs estruturados;
- integração com o backend do HelpDeskLite.