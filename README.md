# Enercheck Backend

Backend em FastAPI para um MVP com:

- API HTTP
- PostgreSQL
- CRUD de usuarios
- integracao de IA via provider
- worker para processamento assincrono
- camada de mensageria preparada para evolucao

## Estrutura

```text
.
|-- docs/
|-- src/
|   |-- app/            # bootstrap da API, configuracao, middleware e rotas
|   |-- db/             # engine, sessao e metadata do banco
|   |-- integrations/   # providers externos, como IA
|   |-- messaging/      # contratos, eventos e adapters de mensageria
|   |-- modules/        # dominio, casos de uso e persistencia por modulo
|   `-- worker/         # entrypoint do worker e processamento assincrono
|-- tests/
|   |-- integration/
|   `-- unit/
|-- .env.example
|-- docker-compose.yml
`-- pyproject.toml
```

## Requisitos

- Python 3.11+
- `uv`
- Docker e Docker Compose para subir o PostgreSQL localmente

## Configuracao

Crie o arquivo de ambiente:

```powershell
Copy-Item .env.example .env
```

Variaveis principais:

- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`
- `DB_NAME`
- `DATABASE_URL` opcional. Se informado, sobrescreve a composicao das variaveis acima.

## Como rodar

### Opcao 1: API local + banco em Docker

1. Instale as dependencias:

```powershell
uv sync
```

2. Suba o banco:

```powershell
docker compose up db -d
```

3. Rode a API:

```powershell
uv run uvicorn src.app.main:app --reload --host 0.0.0.0 --port 8000
```

4. Se quiser o worker:

```powershell
uv run python -m src.worker.main
```

Servicos:

- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- PostgreSQL: `localhost:5432`

## Banco de dados

Credenciais padrao do ambiente local:

- Host: `localhost`
- Port: `5432`
- Database: `enercheck_db`
- User: `enercheck`
- Password: `enercheck123`

No startup da aplicacao, as tabelas sao criadas automaticamente pelo SQLAlchemy.

## Endpoints

### Health

- `GET /health/live`
- `GET /health/ready`

### IA de exemplo

- `POST /v1/ai-demo/respond`
- `POST /v1/ai-demo/jobs`

### Usuarios

- `POST /v1/users`
- `GET /v1/users`
- `GET /v1/users/{user_id}`
- `PUT /v1/users/{user_id}`
- `DELETE /v1/users/{user_id}`

Exemplo de criacao:

```bash
curl -X POST http://localhost:8000/v1/users \
  -H "Content-Type: application/json" \
  -d '{"name":"Maria","email":"maria@example.com"}'
```

Exemplo de atualizacao:

```bash
curl -X PUT http://localhost:8000/v1/users/1 \
  -H "Content-Type: application/json" \
  -d '{"name":"Maria Silva","email":"maria.silva@example.com"}'
```

## Comandos uteis

```powershell
uv run pytest
uv run ruff check .
uv run ruff format .
```

Ou com `make`:

```bash
make api
make worker
make test
make lint
make format
```

## Documentacao complementar

- [Arquitetura](docs/architecture.md)
- [Integracoes de IA](docs/integrations/ai.md)
- [Mensageria](docs/messaging.md)
