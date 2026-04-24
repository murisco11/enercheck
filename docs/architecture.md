# Arquitetura

## Visão geral

O projeto começa como um repositório único com dois processos:

- API FastAPI para exposição HTTP e orquestração síncrona;
- worker para tarefas assíncronas e processamento desacoplado.

Essa abordagem reduz o custo operacional do MVP sem impedir a evolução futura para múltiplos serviços.

## Princípios

- domínio e casos de uso ficam separados de framework e infraestrutura;
- integrações externas entram por adapters;
- contratos internos são mais estáveis que escolhas de vendor;
- o worker consome eventos e chama casos de uso, sem concentrar regra de negócio solta;
- a estrutura de pastas privilegia clareza para onboarding.

## Fronteiras principais

### `src/app`

Contém bootstrap da aplicação, configuração, observabilidade, middleware, tratamento de exceções e rotas.

### `src/modules`

Contém domínio e aplicação. É onde ficam entidades simples, schemas internos e casos de uso.

### `src/integrations`

Contém providers externos. Neste setup, a IA entra por uma interface única e implementações concretas.

### `src/messaging`

Contém contratos de publisher/consumer, definição de eventos e implementações de backend. O backend inicial é em memória.

### `src/worker`

Contém o loop de consumo e o processamento assíncrono dos eventos.

## Caminho de evolução para microsserviços

Se o produto crescer, a extração pode seguir esta ordem:

1. trocar `inmemory` por um broker real;
2. isolar jobs ou integrações pesadas no worker;
3. mover módulos de negócio mais autônomos para serviços independentes;
4. manter contratos de eventos e APIs como fronteiras explícitas.

Enquanto isso não for necessário, o repositório único mantém a entrega mais rápida e a manutenção mais simples.
