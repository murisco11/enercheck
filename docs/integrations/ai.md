# Integrações de IA

## Objetivo

Permitir múltiplos providers sem espalhar detalhes de SDK pelo domínio nem pela camada HTTP.

## Contrato atual

O provider de IA expõe duas operações internas:

- `generate_text(message: str) -> AITextResult`
- `embed_text(text: str) -> AIEmbeddingResult`

Os casos de uso dependem apenas dessa interface.

## Provider inicial

O setup inclui um provider `mock`, útil para:

- desenvolvimento local;
- testes determinísticos;
- demos sem depender de credenciais externas.

## Como adicionar um novo provider

1. criar uma implementação concreta em `src/integrations/ai/`;
2. mapear a seleção no factory;
3. adicionar as variáveis de ambiente necessárias em `Settings`;
4. manter a resposta convertida para os tipos internos.

## Regra importante

SDKs de vendors não devem aparecer em rotas nem em casos de uso. O ponto de acoplamento permitido é o adapter do provider.
