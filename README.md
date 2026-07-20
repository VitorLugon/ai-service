# AI Service

API independente construída com Python e FastAPI para fornecer funcionalidades de inteligência artificial a aplicações internas.

O serviço será inicialmente integrado ao HelpDeskLite e poderá ser reutilizado por outros projetos.

## Funcionalidades atuais

- endpoint de saúde da aplicação;
- endpoint de prontidão;
- configuração por variáveis de ambiente;
- autenticação interna por API Key;
- integração com a OpenAI Responses API;
- serviço inicial de classificação de chamados;
- classificação por categoria, prioridade, resumo e tags;
- estratégias de prompt zero-shot, one-shot e few-shot;
- módulo isolado para construção e teste de prompts;
- critérios explícitos para classificação de prioridade;
- script para comparação qualitativa das estratégias;
- validação dos dados de entrada com Pydantic;
- scripts para validar a conexão e executar classificações reais;
- testes da integração utilizando mocks, sem consumo da API;
- documentação automática com OpenAPI e Swagger UI;
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
│   ├── prompts/      # Estratégias e instruções para os modelos
│   ├── schemas/      # Contratos Pydantic
│   ├── services/     # Operações e integrações
│   └── main.py       # Criação da aplicação FastAPI
├── docs/             # Documentação da arquitetura
├── scripts/          # Instalação, execução e smoke tests
└── tests/            # Testes automatizados
```

A descrição completa está em [`docs/architecture.md`](docs/architecture.md).

## Requisitos

- Python 3.12
- Git
- PowerShell
- chave da OpenAI API para executar funcionalidades reais de inteligência artificial

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

O classificador de chamados ainda não possui um endpoint HTTP.

Atualmente, ele é executado diretamente como um service por meio dos scripts de teste manual.

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

O serviço inicial recebe um chamado com título e descrição:

```json
{
  "title": "Não consigo acessar minha conta",
  "description": "Após redefinir minha senha, o sistema continua informando credenciais inválidas."
}
```

A resposta textual atual segue o formato:

```text
Categoria: acesso_e_autenticacao
Prioridade: alta
Resumo: Usuário não consegue acessar a conta após redefinir a senha.
Tags: login, senha
```

As categorias permitidas são:

- `acesso_e_autenticacao`;
- `erro_tecnico`;
- `cobranca`;
- `duvida_de_uso`;
- `solicitacao`;
- `outro`.

As prioridades permitidas são:

- `baixa`;
- `media`;
- `alta`;
- `critica`.

A resposta ainda é textual. Uma próxima etapa implementará uma saída estruturada e validada pelo Pydantic.

## Testar uma classificação real

Depois de configurar a OpenAI API no `.env`, execute:

```powershell
python -m scripts.classify_ticket_smoke_test
```

Uma saída possível será:

```text
Modelo: gpt-5-mini

Categoria: acesso_e_autenticacao
Prioridade: alta
Resumo: Usuário não consegue acessar o sistema após redefinir a senha.
Tags: login, senha
```

O conteúdo pode variar entre execuções porque a classificação é gerada pelo modelo.

Esse comando utiliza a API real e pode consumir créditos.

## Estratégias de prompt

O classificador suporta três estratégias.

### Zero-shot

Utiliza somente:

- identidade do classificador;
- instruções;
- categorias permitidas;
- prioridades permitidas;
- critérios de prioridade;
- formato esperado.

Nenhum exemplo é fornecido ao modelo.

### One-shot

Utiliza as instruções e uma classificação de exemplo.

O exemplo ajuda o modelo a entender:

- formato da resposta;
- estilo do resumo;
- uso de tags;
- relacionamento entre chamado e classificação.

### Few-shot

Utiliza vários exemplos de chamados e classificações.

Os exemplos atuais incluem:

- cobrança duplicada;
- conta bloqueada;
- indisponibilidade geral do sistema.

O few-shot é utilizado atualmente como baseline padrão do classificador.

Isso não significa que ele será necessariamente a estratégia definitiva. A escolha final deverá ser baseada em avaliações com chamados representativos.

## Comparar estratégias de prompt

Para classificar o mesmo chamado com zero-shot, one-shot e few-shot, execute:

```powershell
python -m scripts.compare_prompt_strategies
```

O fluxo executado será:

```text
Mesmo chamado
    |
    ├── Zero-shot
    ├── One-shot
    └── Few-shot
```

O resultado de cada estratégia será exibido no terminal.

Compare:

- respeito ao formato de quatro linhas;
- uso de categorias permitidas;
- coerência da prioridade;
- qualidade do resumo;
- relevância das tags;
- presença de texto desnecessário.

Esse comando realiza três requisições reais e pode consumir créditos da API.

Os testes executados com `pytest` continuam utilizando mocks e não consomem créditos.

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
- serialização do chamado;
- retorno do serviço de classificação;
- rejeição de respostas vazias do modelo;
- utilização da estratégia de prompt selecionada;
- ausência de exemplos no zero-shot;
- presença de um exemplo no one-shot;
- presença de vários exemplos no few-shot;
- manutenção das categorias e prioridades permitidas.

A integração com a OpenAI é simulada utilizando mocks.

Os testes executados com `pytest`:

- não utilizam uma chave real;
- não realizam requisições externas;
- não consomem créditos da API.

Apenas os scripts de smoke test e comparação utilizam a API real.

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
- analisar apenas o problema relatado;
- manter a saída dentro do formato solicitado.

## Próximas funcionalidades

- saída estruturada para classificação de chamados;
- validação de categoria, prioridade, resumo e tags com Pydantic;
- endpoint `POST /internal/tickets/classify`;
- tratamento estruturado de erros da OpenAI API;
- testes para timeout, rate limit e falhas do provedor;
- avaliação com um conjunto representativo de chamados;
- integração com o backend do HelpDeskLite;
- observabilidade e logs estruturados.