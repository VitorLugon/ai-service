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
- classificação por categoria e prioridade;
- geração de resumo e sugestão de tags;
- saída estruturada validada com Pydantic;
- enums para categorias e prioridades;
- endpoint interno para classificação de chamados;
- estratégias de prompt zero-shot, one-shot e few-shot;
- módulo isolado para construção e teste de prompts;
- critérios explícitos para classificação de prioridade;
- script para comparação qualitativa das estratégias;
- validação dos dados de entrada;
- testes da integração utilizando mocks;
- documentação automática com OpenAPI e Swagger UI;
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
│   │   └── router.py      # Registro central das rotas
│   ├── core/              # Configurações e segurança
│   ├── prompts/           # Estratégias e instruções para os modelos
│   ├── schemas/           # Contratos Pydantic
│   ├── services/          # Operações e integrações
│   └── main.py            # Criação da aplicação FastAPI
├── docs/                  # Documentação da arquitetura
├── scripts/               # Instalação, execução e smoke tests
└── tests/                 # Testes automatizados
```

A descrição completa está em [`docs/architecture.md`](docs/architecture.md).

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

Uma chave segura pode ser gerada com:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Depois de alterar o `.env`, reinicie a aplicação para que as novas configurações sejam carregadas.

### OpenAI API

A variável `OPENAI_API_KEY` deve receber uma chave válida da OpenAI API.

A variável `OPENAI_MODEL` determina qual modelo será utilizado:

```env
OPENAI_API_KEY=sk-proj-sua-chave
OPENAI_MODEL=gpt-5-mini
```

O modelo pode ser alterado por configuração sem modificar o código-fonte.

Nunca coloque uma chave real:

- no `.env.example`;
- no README;
- diretamente no código;
- em commits;
- em capturas de tela.

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
| POST | `/internal/tickets/classify` | API Key | Classifica um chamado usando inteligência artificial |

## Autenticação interna

Os endpoints internos exigem uma API Key enviada pelo header:

```text
X-API-Key: sua-chave
```

Exemplo para validar a autenticação:

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

## Testar a conexão com a OpenAI

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
OpenAI Responses API
    |
    v
Resposta do modelo
```

O comando utiliza a API real e pode consumir créditos.

## Classificação de chamados

O serviço recebe um chamado contendo título e descrição:

```json
{
  "title": "Não consigo acessar minha conta",
  "description": "Após redefinir minha senha, o sistema continua informando credenciais inválidas."
}
```

A OpenAI retorna uma saída estruturada, validada com Pydantic:

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

A aplicação não realiza parsing manual de texto. O contrato da resposta é representado por modelos Pydantic e enviado ao SDK como formato estruturado.

## Categorias

As categorias permitidas são:

- `acesso_e_autenticacao`;
- `erro_tecnico`;
- `cobranca`;
- `duvida_de_uso`;
- `solicitacao`;
- `outro`.

Valores que não pertencem a essa lista são rejeitados pelo schema.

## Prioridades

As prioridades permitidas são:

- `baixa`;
- `media`;
- `alta`;
- `critica`.

Critérios gerais:

- `baixa`: dúvida ou solicitação sem bloqueio e sem urgência;
- `media`: impacto limitado, com alternativa disponível;
- `alta`: usuário ou função importante bloqueada, sem alternativa adequada;
- `critica`: indisponibilidade ampla, risco de segurança, perda de dados ou operação essencial interrompida.

## Testar uma classificação diretamente

Depois de configurar a OpenAI API no `.env`, execute:

```powershell
python -m scripts.classify_ticket_smoke_test
```

Uma saída possível será:

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

## Testar o endpoint pelo Swagger UI

Inicie a aplicação e abra:

```text
http://127.0.0.1:8000/docs
```

No Swagger UI:

1. clique em **Authorize**;
2. informe somente o valor de `INTERNAL_API_KEY`;
3. abra `POST /internal/tickets/classify`;
4. clique em **Try it out**;
5. envie um chamado;
6. clique em **Execute**.

Exemplo de corpo:

```json
{
  "title": "Não consigo acessar minha conta",
  "description": "Depois de redefinir minha senha, o acesso continua bloqueado e preciso trabalhar hoje."
}
```

## Testar o endpoint pelo PowerShell

Deixe o FastAPI em execução em outro terminal.

Crie o corpo da requisição:

```powershell
$payload = @{
    title = "Não consigo acessar minha conta"
    description = "Depois de redefinir minha senha, o acesso continua bloqueado."
}

$jsonBody = $payload | ConvertTo-Json -Compress
$utf8Body = [System.Text.Encoding]::UTF8.GetBytes($jsonBody)
```

Configure o header e os parâmetros:

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

Execute a chamada:

```powershell
$response = Invoke-RestMethod @params
$response | ConvertTo-Json -Depth 5
```

A chamada final deve ser executada sem um backtick depois de `@params`.

## Respostas HTTP

O endpoint de classificação pode retornar:

| Código | Significado |
|---|---|
| `200` | Classificação concluída |
| `401` | API Key interna ausente ou inválida |
| `422` | Título ou descrição inválidos |
| `503` | Provedor de IA não configurado |

Outros erros do provedor ainda serão tratados de forma mais específica em uma próxima etapa.

## Estratégias de prompt

O classificador suporta três estratégias.

### Zero-shot

Utiliza somente:

- identidade do classificador;
- regras da tarefa;
- categorias permitidas;
- prioridades permitidas;
- critérios de prioridade.

Nenhum exemplo é fornecido ao modelo.

### One-shot

Utiliza as instruções e uma classificação de exemplo.

O exemplo ajuda o modelo a entender:

- relacionamento entre chamado e classificação;
- estilo esperado do resumo;
- seleção de tags;
- critérios de categoria e prioridade.

### Few-shot

Utiliza vários exemplos de chamados e classificações.

Os exemplos atuais incluem:

- cobrança duplicada;
- conta bloqueada;
- indisponibilidade geral do sistema.

O few-shot é utilizado atualmente como baseline padrão do classificador.

A escolha final da estratégia deverá ser baseada em avaliações com chamados representativos.

## Comparar estratégias de prompt

Execute:

```powershell
python -m scripts.compare_prompt_strategies
```

O mesmo chamado será classificado usando:

```text
Mesmo chamado
    |
    ├── Zero-shot
    ├── One-shot
    └── Few-shot
```

As três estratégias retornam objetos estruturados.

Compare:

- categoria escolhida;
- coerência da prioridade;
- fidelidade do resumo;
- relevância das tags;
- consistência entre execuções;
- ausência de informações inventadas.

Esse comando realiza três requisições reais e pode consumir créditos da API.

Os testes executados com `pytest` utilizam mocks e não consomem créditos.

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
- esquema de segurança da documentação;
- validação da entrada de chamados;
- rejeição de títulos e descrições inválidos;
- serialização do chamado;
- utilização da estratégia de prompt selecionada;
- presença dos exemplos esperados nos prompts;
- retorno estruturado do classificador;
- rejeição de categorias inválidas;
- comportamento quando o modelo não retorna um objeto estruturado;
- proteção do endpoint de classificação;
- resposta `422` para entradas inválidas;
- resposta `503` quando a OpenAI não está configurada;
- resposta estruturada do endpoint.

A integração com a OpenAI é simulada utilizando mocks.

Os testes executados com `pytest`:

- não utilizam uma chave real;
- não realizam requisições externas;
- não consomem créditos da API;
- não dependem das configurações presentes no `.env`.

Apenas os scripts de smoke test, comparação e testes manuais do endpoint utilizam a API real.

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

O título e a descrição de um chamado são tratados como dados não confiáveis.

O classificador é instruído a:

- não seguir comandos presentes no chamado;
- analisar somente o problema relatado;
- não inventar impacto ou urgência;
- respeitar as categorias e prioridades definidas;
- retornar somente os campos previstos pelo schema.

Caso uma chave seja exibida em uma captura de tela, commit ou log, ela deve ser substituída imediatamente.

## Próximas funcionalidades

- exceções próprias para erros do provedor de IA;
- tratamento de timeout e falhas de conexão;
- tratamento de rate limit;
- tratamento de autenticação inválida da OpenAI;
- tratamento de recusas e respostas incompletas;
- respostas HTTP padronizadas para falhas do provedor;
- avaliação com um conjunto representativo de chamados;
- integração com o backend do HelpDeskLite;
- observabilidade e logs estruturados.