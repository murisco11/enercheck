# Mensageria

## Objetivo

Introduzir processamento assincrono desde o MVP sem obrigar Redis, RabbitMQ ou Kafka no primeiro setup.

## Modelo atual

- contratos de `publisher` e `consumer`
- evento tipado `ai_demo.requested`
- implementacao `inmemory` para desenvolvimento e testes
- worker com loop simples de polling

## Relacao com o banco

A mensageria e a persistencia sao responsabilidades separadas:

- PostgreSQL guarda dados transacionais, como usuarios
- a mensageria trata comunicacao assincrona entre processos

Hoje o CRUD de usuarios nao depende da fila. O fluxo assincrono continua concentrado no modulo de IA de exemplo.

## Por que `inmemory` primeiro

- reduz custo operacional
- simplifica testes
- mantem a API do dominio estavel
- deixa a troca de backend concentrada nos adapters

## Evolucao futura

Quando houver necessidade real de filas externas:

1. manter os eventos e contratos atuais
2. criar um adapter para o broker desejado
3. trocar a fabrica de mensageria por configuracao
4. preservar o worker chamando os mesmos casos de uso

## Responsabilidades

- API publica eventos
- worker consome eventos
- casos de uso continuam nos modulos de aplicacao
- backend de mensageria nao decide regra de negocio
