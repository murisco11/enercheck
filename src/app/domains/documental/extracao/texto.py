"""Extração de texto bruto de PDFs em dois modos complementares.

Faturas têm layouts em colunas e, dependendo da região, um modo de leitura recupera
melhor que o outro:

- ``layout``: ``pdftotext -layout`` (poppler) preserva a disposição espacial — ideal
  para o cabeçalho da NF3e (Neoenergia), que a leitura por fluxo embaralha.
- ``fluxo``: ordem de leitura do ``pdfplumber`` — recupera corretamente a tabela de
  itens de layouts mais antigos (Cosern 2022), em que as colunas ficam desalinhadas
  na visão espacial.

Cada extrator escolhe o modo mais confiável para o seu layout. Quando o binário
``pdftotext`` não está disponível, ``layout`` recai em ``pdfplumber(layout=True)``.
"""

import logging
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

SEPARADOR_PAGINA = "\f"


@dataclass(frozen=True)
class DocumentoTexto:
    layout: str
    fluxo: str

    @property
    def paginas_layout(self) -> list[str]:
        return self.layout.split(SEPARADOR_PAGINA)


def extrair_documento_texto(conteudo: bytes) -> DocumentoTexto:
    return DocumentoTexto(layout=_texto_layout(conteudo), fluxo=_texto_fluxo(conteudo))


def _texto_layout(conteudo: bytes) -> str:
    via_poppler = _via_pdftotext(conteudo)
    if via_poppler is not None and via_poppler.strip():
        return via_poppler
    return _via_pdfplumber(conteudo, layout=True)


def _texto_fluxo(conteudo: bytes) -> str:
    return _via_pdfplumber(conteudo, layout=False)


def _via_pdftotext(conteudo: bytes) -> str | None:
    executavel = shutil.which("pdftotext")
    if executavel is None:
        return None
    with tempfile.TemporaryDirectory() as tmp:
        origem = Path(tmp) / "doc.pdf"
        origem.write_bytes(conteudo)
        try:
            resultado = subprocess.run(  # noqa: S603 - binário confiável do poppler
                [executavel, "-layout", "-enc", "UTF-8", str(origem), "-"],
                capture_output=True,
                timeout=120,
            )
        except (subprocess.SubprocessError, OSError) as exc:
            logger.warning("pdftotext falhou, usando fallback pdfplumber: %s", exc)
            return None
        if resultado.returncode != 0:
            logger.warning("pdftotext retornou %s, usando fallback", resultado.returncode)
            return None
        return resultado.stdout.decode("utf-8", errors="replace")


def _via_pdfplumber(conteudo: bytes, *, layout: bool) -> str:
    import pdfplumber

    partes: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        origem = Path(tmp) / "doc.pdf"
        origem.write_bytes(conteudo)
        with pdfplumber.open(str(origem)) as pdf:
            for pagina in pdf.pages:
                partes.append(pagina.extract_text(layout=layout) or "")
    return SEPARADOR_PAGINA.join(partes)
