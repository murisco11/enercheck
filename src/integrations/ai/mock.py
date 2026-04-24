from src.integrations.ai.base import AIEmbeddingResult, AITextResult


class MockAIProvider:
    def __init__(self, prefix: str) -> None:
        self._prefix = prefix

    async def generate_text(self, message: str) -> AITextResult:
        return AITextResult(
            provider="mock",
            output=f"{self._prefix} Resposta simulada para: {message}",
        )

    async def embed_text(self, text: str) -> AIEmbeddingResult:
        seed = float(len(text))
        return AIEmbeddingResult(provider="mock", vector=[seed, seed / 10, seed / 100])
