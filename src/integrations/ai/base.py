from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class AITextResult:
    provider: str
    output: str


@dataclass(slots=True)
class AIEmbeddingResult:
    provider: str
    vector: list[float]


class AIProvider(Protocol):
    async def generate_text(self, message: str) -> AITextResult:
        """Gera texto a partir da mensagem."""

    async def embed_text(self, text: str) -> AIEmbeddingResult:
        """Gera embedding interno para a string."""
