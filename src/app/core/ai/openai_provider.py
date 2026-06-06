import json
from typing import Any

from src.app.core.exceptions import IntegrationError


class OpenAIProvider:
    """Provider de IA baseado na API da OpenAI.

    Usa Structured Outputs (response_format json_schema) para a extração de fallback,
    garantindo que a resposta respeite exatamente o schema do modelo canônico.
    """

    nome = "openai"

    def __init__(
        self,
        api_key: str,
        modelo_extracao: str,
        modelo_embedding: str,
    ) -> None:
        if not api_key:
            raise IntegrationError("OPENAI_API_KEY não configurada.")
        # Import tardio para não exigir o pacote quando AI_PROVIDER=mock.
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)
        self._modelo_extracao = modelo_extracao
        self._modelo_embedding = modelo_embedding

    def extrair_estruturado(
        self,
        texto: str,
        json_schema: dict[str, Any],
        instrucoes: str,
    ) -> dict[str, Any]:
        try:
            resposta = self._client.chat.completions.create(
                model=self._modelo_extracao,
                messages=[
                    {"role": "system", "content": instrucoes},
                    {"role": "user", "content": texto},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "extracao_fatura",
                        "schema": json_schema,
                        "strict": True,
                    },
                },
                temperature=0,
            )
        except Exception as exc:  # noqa: BLE001 - normaliza erro de integração
            raise IntegrationError(f"Falha na extração via OpenAI: {exc}") from exc

        conteudo = resposta.choices[0].message.content
        if not conteudo:
            raise IntegrationError("Resposta vazia da OpenAI na extração.")
        return json.loads(conteudo)

    def completar(self, prompt: str, *, instrucoes: str | None = None) -> str:
        mensagens: list[dict[str, str]] = []
        if instrucoes:
            mensagens.append({"role": "system", "content": instrucoes})
        mensagens.append({"role": "user", "content": prompt})
        try:
            resposta = self._client.chat.completions.create(
                model=self._modelo_extracao,
                messages=mensagens,
                temperature=0.2,
            )
        except Exception as exc:  # noqa: BLE001
            raise IntegrationError(f"Falha na geração de texto via OpenAI: {exc}") from exc
        return resposta.choices[0].message.content or ""

    def embed(self, textos: list[str]) -> list[list[float]]:
        try:
            resposta = self._client.embeddings.create(
                model=self._modelo_embedding,
                input=textos,
            )
        except Exception as exc:  # noqa: BLE001
            raise IntegrationError(f"Falha na geração de embeddings via OpenAI: {exc}") from exc
        return [item.embedding for item in resposta.data]
