# Mensageria

## Objetivo

Introduzir processamento assíncrono desde o MVP sem obrigar Redis, RabbitMQ ou Kafka no primeiro setup.

## Modelo atual

- contratos de `publisher` e `consumer`;
- evento tipado `ai_demo.requested`;
- implementação `inmemory` para desenvolvimento e testes;
- worker com loop simples de polling.

## Por que `inmemory` primeiro

- reduz custo operacional;
- simplifica testes;
- mantém a API do domínio estável;
- deixa a troca de backend concentrada nos adapters.

## Evolução futura

Quando houver necessidade real de filas externas:

1. manter os eventos e contratos atuais;
2. criar um adapter para o broker desejado;
3. trocar a fábrica de mensageria por configuração;
4. preservar o worker chamando os mesmos casos de uso.

## Responsabilidades

- API publica eventos;
- worker consome eventos;
- casos de uso continuam no domínio/aplicação;
- backend de mensageria não decide regra de negócio.
