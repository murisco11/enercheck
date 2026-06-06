from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class AIProvider(Protocol):
    """Contrato da camada de IA.

    A IA é uma camada de apoio: extrai/organiza informação e (futuramente) redige
    textos e gera embeddings. Ela nunca origina o valor recuperável — isso é papel
    exclusivo do motor determinístico.
    """

    nome: str

    def extrair_estruturado(
        self,
        texto: str,
        json_schema: dict[str, Any],
        instrucoes: str,
    ) -> dict[str, Any]:
        """Extrai dados estruturados de um texto livre conforme um JSON Schema.

        Usado apenas como *fallback* quando nenhum extrator determinístico de layout
        consegue ler a fatura com confiança suficiente.
        """
        ...

    def completar(self, prompt: str, *, instrucoes: str | None = None) -> str:
        """Gera um texto livre a partir de um prompt (apoio a dossiês/explicações)."""
        ...

    def embed(self, textos: list[str]) -> list[list[float]]:
        """Gera embeddings para uma lista de textos (apoio a RAG)."""
        ...
