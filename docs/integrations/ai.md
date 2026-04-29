# Integracoes de IA

## Objetivo

Permitir multiplos providers sem espalhar detalhes de SDK pelo dominio, pela camada HTTP ou pela persistencia.

## Contrato atual

O provider de IA expoe operacoes internas para os casos de uso.

No estado atual, o fluxo HTTP demonstrado usa:

- `generate_text(message: str)`

Os casos de uso dependem apenas da interface, nao do SDK do vendor.

## Provider inicial

O projeto inclui um provider `mock`, util para:

- desenvolvimento local
- testes deterministicos
- demos sem credenciais externas

## Como adicionar um novo provider

1. criar uma implementacao concreta em `src/integrations/ai/`
2. mapear a selecao no factory
3. adicionar as variaveis de ambiente necessarias em `Settings`
4. manter a resposta convertida para os tipos internos

## Regra importante

SDKs de vendors nao devem aparecer em rotas, repositorios ou casos de uso. O ponto de acoplamento permitido e o adapter do provider.
