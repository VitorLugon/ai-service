## Endpoints

| Método | Endpoint | Descrição |
|---|---|---|
| GET | `/health` | Verifica se o processo da aplicação está funcionando |
| GET | `/ready` | Verifica se a aplicação está pronta para receber requisições |

## Executar localmente

```bash
fastapi dev app/main.py