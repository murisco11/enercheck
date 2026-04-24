# Enercheck

Base de projeto FastAPI para um MVP com integrações de IA, worker assíncrono e fronteiras preparadas para evoluir para microsserviços sem carregar a complexidade total desde o primeiro dia.

## Objetivos do setup

- manter a API principal simples para desenvolver e operar;
- isolar integrações de IA por provider;
- introduzir um worker separado para fluxos assíncronos;
- abstrair mensageria para permitir troca futura de backend;
- documentar a arquitetura e as convenções do repositório.

## Estrutura do projeto

```text
.
|-- docs/
|-- src/
|   |-- app/            # bootstrap da API, configuração, middleware e rotas
|   |-- integrations/   # providers externos, como IA
|   |-- messaging/      # contratos, eventos e adapters de mensageria
|   |-- modules/        # domínio e casos de uso
|   `-- worker/         # entrypoint do worker e processamento assíncrono
|-- tests/
|   |-- integration/
|   `-- unit/
|-- .env.example
`-- pyproject.toml
```

## Requisitos

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) para dependências e execução local

## Como começar

```bash
uv sync
cp .env.example .env
```

## Comandos principais

```bash
make api
make worker
make test
make lint
make format
```

Se você estiver no Windows sem `make`, use os equivalentes:

```powershell
uv run uvicorn src.app.main:app --reload --host 0.0.0.0 --port 8000
uv run python -m src.worker.main
uv run pytest
uv run ruff check .
uv run ruff format .
```

## Endpoints iniciais

- `GET /health/live`: liveness probe
- `GET /health/ready`: readiness probe
- `POST /v1/ai-demo/respond`: fluxo síncrono de exemplo com provider de IA
- `POST /v1/ai-demo/jobs`: cria job assíncrono de demonstração para o worker

Exemplo do fluxo síncrono:

```bash
curl -X POST http://localhost:8000/v1/ai-demo/respond \
  -H "Content-Type: application/json" \
  -d '{"message":"Explique o objetivo deste MVP"}'
```

Exemplo do fluxo assíncrono:

```bash
curl -X POST http://localhost:8000/v1/ai-demo/jobs \
  -H "Content-Type: application/json" \
  -d '{"message":"Processar este item em background"}'
```

## Configuração

As variáveis de ambiente ficam centralizadas em `src/app/core/config.py`. O setup já separa:

- app e ambiente;
- observabilidade;
- provider de IA;
- backend de mensageria;
- polling do worker.

## IA e mensageria

- A camada de IA expõe contratos internos estáveis e evita acoplamento direto ao SDK de vendor.
- A mensageria começa com backend `inmemory`, suficiente para desenvolvimento local e testes.
- A extração futura para Redis, RabbitMQ ou outro broker deve acontecer só nos adapters, sem reescrever casos de uso.

## Documentação complementar

- [Arquitetura](docs/architecture.md)
- [Integrações de IA](docs/integrations/ai.md)
- [Mensageria](docs/messaging.md)

## Próximos passos sugeridos

- adicionar autenticação e autorização;
- incluir provider real de IA;
- plugar broker real de mensageria;
- adicionar observabilidade com tracing e métricas.
