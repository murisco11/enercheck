from typing import Any

from src.app.core.exceptions import IntegrationError


class MockAIProvider:
    """Provider de IA para desenvolvimento e testes.

    Não chama nenhuma API externa. A extração estruturada é intencionalmente
    indisponível: o fluxo de testes depende dos extratores determinísticos de
    layout, e qualquer fallback de IA num ambiente sem chave deve falhar de forma
    explícita em vez de inventar dados.
    """

    nome = "mock"

    def __init__(self, prefixo: str = "[mock-ai]") -> None:
        self._prefixo = prefixo

    def extrair_estruturado(
        self,
        texto: str,
        json_schema: dict[str, Any],
        instrucoes: str,
    ) -> dict[str, Any]:
        raise IntegrationError(
            "Extração via IA indisponível no provider 'mock'. "
            "Cadastre um layout determinístico ou configure AI_PROVIDER=openai."
        )

    def completar(self, prompt: str, *, instrucoes: str | None = None) -> str:
        return f"{self._prefixo} {prompt}".strip()

    def embed(self, textos: list[str]) -> list[list[float]]:
        # Vetor determinístico e nulo apenas para não quebrar fluxos de teste.
        return [[0.0] for _ in textos]
