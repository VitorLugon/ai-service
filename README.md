# AI Service

Serviço em Python e FastAPI responsável pelas funcionalidades de inteligência artificial e integração com aplicações internas.

## Endpoints

| Método | Endpoint | Autenticação | Descrição |
|---|---|---|---|
| GET | `/health` | Não | Verifica se o processo da aplicação está funcionando |
| GET | `/ready` | Não | Verifica se a aplicação está pronta para receber requisições |
| GET | `/internal/ping` | API Key | Valida a autenticação entre serviços internos |

## Executar localmente

Ative o ambiente virtual:

```powershell
.venv\Scripts\Activate.ps1
```

Inicie a aplicação:

```bash
fastapi dev app/main.py
```

A documentação interativa estará disponível em:

```text
http://127.0.0.1:8000/docs
```

## Autenticação interna

Os endpoints internos exigem uma API Key enviada pelo header:

```text
X-API-Key: sua-chave
```

A chave deve ser configurada no arquivo `.env`:

```env
INTERNAL_API_KEY=sua-chave
```

Exemplo com `curl`:

```bash
curl -H "X-API-Key: sua-chave" \
  http://127.0.0.1:8000/internal/ping
```

No Windows PowerShell:

```powershell
curl.exe `
  -H "X-API-Key: SUA_CHAVE" `
  http://127.0.0.1:8000/internal/ping
```

As rotas `/health` e `/ready` são públicas e não exigem autenticação.

Nunca envie o arquivo `.env` ou chaves reais para o repositório.

## Qualidade do código

Execute todas as verificações antes de enviar alterações:

```bash
ruff check .
ruff format --check .
mypy app
pytest
```

Os testes possuem cobertura mínima obrigatória de 90%.

O GitHub Actions executa automaticamente lint, verificação de formatação, análise de tipos e testes em cada push ou pull request para a branch `main`.