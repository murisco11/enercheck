# Arquitetura

## Visao geral

O projeto hoje roda como um repositorio unico com tres blocos principais:

- API FastAPI para exposicao HTTP
- PostgreSQL para persistencia
- worker para fluxos assincronos

Essa composicao mantem o MVP simples de operar, mas ja separa responsabilidades para crescimento futuro.

## Principios

- dominio e casos de uso ficam separados de framework e infraestrutura
- persistencia entra por modulo, sem espalhar SQL pela camada HTTP
- integracoes externas entram por adapters
- contratos internos devem ser mais estaveis que escolhas de vendor
- o worker consome eventos e chama casos de uso

## Fronteiras principais

### `src/app`

Bootstrap da aplicacao, configuracao, middleware, tratamento de excecoes, dependencias e rotas.

### `src/db`

Infraestrutura compartilhada de banco:

- engine do SQLAlchemy
- session factory
- metadata base
- carregamento dos modelos ORM

### `src/modules`

Organizacao por modulo de negocio.

No estado atual:

- `ai_demo` para o fluxo de IA de exemplo
- `users` para o CRUD de usuarios

Cada modulo pode conter:

- `domain`
- `application`
- `infrastructure`

### `src/integrations`

Providers externos, como a integracao de IA.

### `src/messaging`

Contratos de publisher/consumer, definicao de eventos e implementacoes do backend de mensageria.

### `src/worker`

Loop de consumo e processamento assincrono de eventos.

## Fluxos principais

### CRUD de usuarios

1. A rota HTTP recebe o payload.
2. O caso de uso do modulo `users` orquestra a operacao.
3. O repositorio SQLAlchemy acessa o PostgreSQL.
4. A resposta volta em schema HTTP.

### Job assincrono de IA

1. A API publica um evento.
2. O worker consome esse evento.
3. O caso de uso executa a logica necessaria.

## Persistencia

O banco padrao e PostgreSQL, configurado por variaveis de ambiente.

Se `DATABASE_URL` nao for informada, a URL e montada a partir de:

- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`
- `DB_NAME`

As tabelas sao criadas no startup da aplicacao.

## Evolucao natural

Quando o projeto crescer, a evolucao mais provavel e:

1. introduzir migracoes com Alembic
2. trocar a mensageria `inmemory` por Redis, RabbitMQ ou similar
3. separar modulos de negocio mais autonomos em servicos independentes
4. manter eventos e contratos HTTP como fronteiras explicitas
