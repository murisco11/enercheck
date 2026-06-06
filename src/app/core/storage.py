from functools import lru_cache
from pathlib import Path
from typing import Protocol

from src.app.core.config import get_settings
from src.app.core.exceptions import NaoEncontradoError


class ObjectStorage(Protocol):
    """Armazenamento bruto dos arquivos originais (camada original da especificação).

    Guarda os PDFs/imagens preservando o hash para permitir reprocessamento e prova
    de rastreabilidade.
    """

    def salvar(self, conteudo: bytes, sha256: str, *, extensao: str = "") -> str: ...

    def ler(self, uri: str) -> bytes: ...


class LocalObjectStorage:
    """Implementação em filesystem local, com sharding pelo prefixo do sha256."""

    def __init__(self, base_dir: str) -> None:
        self._base = Path(base_dir)

    def salvar(self, conteudo: bytes, sha256: str, *, extensao: str = "") -> str:
        sufixo = extensao if extensao.startswith(".") or not extensao else f".{extensao}"
        destino = self._caminho(sha256, sufixo)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(conteudo)
        return destino.relative_to(self._base).as_posix()

    def ler(self, uri: str) -> bytes:
        caminho = self._base / uri
        if not caminho.exists():
            raise NaoEncontradoError(f"Arquivo não encontrado no storage: {uri}")
        return caminho.read_bytes()

    def _caminho(self, sha256: str, sufixo: str) -> Path:
        return self._base / sha256[:2] / f"{sha256}{sufixo}"


@lru_cache
def get_object_storage() -> ObjectStorage:
    return LocalObjectStorage(get_settings().storage_dir)
