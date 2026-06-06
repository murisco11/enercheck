"""Detecção de layout por assinatura textual.

`LayoutFatura.assinatura_deteccao` é um JSON com âncoras de texto:
``{"all": [...], "any": [...]}`` — todas as âncoras de ``all`` devem estar presentes
e (se houver) ao menos uma de ``any``. A comparação é feita sobre os dois modos de
texto (layout e fluxo) para tolerar variações de extração.
"""

from src.app.domains.documental.extracao.texto import DocumentoTexto


def detectar(doc: DocumentoTexto, layouts: list) -> object | None:  # noqa: ANN001
    corpus = f"{doc.layout}\n{doc.fluxo}"
    for layout in layouts:
        if not getattr(layout, "ativo", True):
            continue
        if _casa(corpus, layout.assinatura_deteccao):
            return layout
    return None


def _casa(corpus: str, assinatura: dict | None) -> bool:
    if not assinatura:
        return False
    todas = assinatura.get("all", [])
    qualquer = assinatura.get("any", [])
    if any(ancora not in corpus for ancora in todas):
        return False
    if qualquer and not any(ancora in corpus for ancora in qualquer):
        return False
    return bool(todas or qualquer)
