# AI Service

API independente construída com Python e FastAPI para fornecer funcionalidades de inteligência artificial a aplicações internas.

O serviço será inicialmente integrado ao HelpDeskLite e poderá ser reutilizado por outros projetos.

## Funcionalidades atuais

- endpoint de saúde da aplicação;
- endpoint de prontidão;
- configuração por variáveis de ambiente;
- autenticação interna por API Key;
- documentação OpenAPI;
- testes automatizados;
- cobertura mínima de testes;
- lint e formatação com Ruff;
- análise estática com mypy;
- integração contínua com GitHub Actions.

## Tecnologias

- Python 3.12
- FastAPI
- Pydantic
- pydantic-settings
- pytest
- pytest-cov
- Ruff
- mypy
- GitHub Actions

## Arquitetura

```text
app/
├── api/          # Rotas e configuração HTTP
├── core/         # Configurações e segurança
├── schemas/      # Contratos Pydantic
├── services/     # Operações e regras da aplicação
└── main.py       # Criação da aplicação
```

A descrição completa está em [`docs/architecture.md`](docs/architecture.md).

## Requisitos

- Python 3.12
- Git
- PowerShell

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

Depois, configure uma chave segura no `.env`:

```env
INTERNAL_API_KEY=sua-chave-secreta
```

Uma chave pode ser gerada com:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Executar localmente

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

## Endpoints

| Método | Endpoint | Autenticação | Descrição |
|---|---|---|---|
| GET | `/health` | Não | Verifica se o processo está funcionando |
| GET | `/ready` | Não | Verifica se o serviço está pronto |
| GET | `/internal/ping` | API Key | Valida a autenticação entre serviços |

## Autenticação interna

Os endpoints internos exigem o header:

```text
X-API-Key: sua-chave
```

Exemplo no PowerShell:

```powershell
curl.exe `
  -H "X-API-Key: SUA_CHAVE" `
  http://127.0.0.1:8000/internal/ping
```

As rotas `/health` e `/ready` são públicas.

O arquivo `.env` e as chaves reais nunca devem ser enviados ao repositório.

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

Os testes exigem cobertura mínima de 90%.

## Integração contínua

O GitHub Actions executa automaticamente:

- lint;
- verificação de formatação;
- análise de tipos;
- testes;
- validação da cobertura.

O workflow é executado em pushes e pull requests para a branch `main`.

## Próximas funcionalidades

- classificação automática de chamados;
- geração de resumos;
- integração com modelos de linguagem;
- tratamento estruturado de erros;
- observabilidade e logs estruturados;
- integração com o backend do HelpDeskLite.