"""Testa a extração determinística em lote, sem banco, servidor ou OpenAI.

Roda o pipeline de extração sobre um ou mais PDFs/pastas e imprime o que foi lido
de cada um — útil para avaliar quais layouts já são reconhecidos antes de ligar a
IA. O provider de IA é forçado para mock, então a chave da OpenAI nunca é usada:
layouts não reconhecidos aparecem como "não reconhecido" em vez de cair no fallback.

Uso::

    uv run python -m scripts.testar_extracao "C:/caminho/para/pasta"
    uv run python -m scripts.testar_extracao conta1.pdf conta2.pdf
    uv run python -m scripts.testar_extracao            # usa ~/Downloads
"""

import sys
from pathlib import Path
from types import SimpleNamespace

from src.app.core.ai.mock import MockAIProvider
from src.app.core.exceptions import IntegrationError
from src.app.domains.documental.extracao import executar_extracao

# Layouts conhecidos (mesmas assinaturas do seed), para detecção offline.
LAYOUTS = [
    SimpleNamespace(
        codigo="cosern_2022",
        extrator_classe="cosern_2022",
        ativo=True,
        assinatura_deteccao={"all": ["DESCRIÇÃO DA NOTA FISCAL", "DEMONSTRATIVO DE CONSUMO"]},
    ),
    SimpleNamespace(
        codigo="cosern_nf3e",
        extrator_classe="cosern_nf3e",
        ativo=True,
        assinatura_deteccao={"all": ["ITENS DA FATURA"], "any": ["chave de acesso", "DANFE"]},
    ),
]


def _coletar_pdfs(args: list[str]) -> list[Path]:
    alvos = [Path(a) for a in args] if args else [Path.home() / "Downloads"]
    pdfs: list[Path] = []
    for alvo in alvos:
        if alvo.is_dir():
            pdfs.extend(sorted(alvo.glob("*.pdf")))
        elif alvo.suffix.lower() == ".pdf" and alvo.exists():
            pdfs.append(alvo)
    return pdfs


def _testar(pdf: Path) -> None:
    print(f"\n=== {pdf.name} ===")
    try:
        resultado = executar_extracao(
            pdf.read_bytes(),
            LAYOUTS,
            provider=MockAIProvider(),
            confianca_minima=0.0,  # nunca aciona o fallback de IA
        )
    except IntegrationError:
        print("  layout NÃO reconhecido (precisaria do fallback de IA ou de um novo extrator).")
        return
    except Exception as exc:  # noqa: BLE001
        print(f"  ERRO ao extrair: {exc}")
        return

    print(f"  layout: {resultado.layout_codigo} | método: {resultado.metodo} "
          f"| confiança: {resultado.confianca} | faturas: {len(resultado.faturas)}")
    for f in resultado.faturas:
        consumo = f.medidas[0].consumo_kwh if f.medidas else "?"
        chave = f.chave_acesso or "—"
        print(f"    • {f.competencia} | total R$ {f.valor_total} | consumo {consumo} kWh "
              f"| itens {len(f.itens)} | chave {chave}")


def main() -> None:
    pdfs = _coletar_pdfs(sys.argv[1:])
    if not pdfs:
        print("Nenhum PDF encontrado. Informe um arquivo ou pasta.")
        return
    print(f"Testando {len(pdfs)} PDF(s)...")
    for pdf in pdfs:
        _testar(pdf)


if __name__ == "__main__":
    main()
