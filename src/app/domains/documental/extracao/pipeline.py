"""Pipeline de extração: texto → detecção de layout → extrator → fallback de IA."""

import logging

from src.app.core.ai import AIProvider, get_ai_provider
from src.app.core.config import get_settings
from src.app.core.exceptions import IntegrationError
from src.app.domains.documental.extracao.detector import detectar
from src.app.domains.documental.extracao.llm_extractor import extrair_via_ia
from src.app.domains.documental.extracao.registry import obter_extrator
from src.app.domains.documental.extracao.schema import ResultadoExtracao
from src.app.domains.documental.extracao.texto import extrair_documento_texto

logger = logging.getLogger(__name__)


def executar_extracao(
    conteudo: bytes,
    layouts: list,  # noqa: ANN001 - list[LayoutFatura]
    *,
    provider: AIProvider | None = None,
    confianca_minima: float | None = None,
) -> ResultadoExtracao:
    settings = get_settings()
    limite = settings.extracao_confianca_minima if confianca_minima is None else confianca_minima
    provider = provider or get_ai_provider()

    doc = extrair_documento_texto(conteudo)
    resultado = _deterministico(doc, layouts)

    if resultado is not None and resultado.confianca >= limite:
        return resultado

    try:
        via_ia = extrair_via_ia(doc, provider)
    except IntegrationError as exc:
        logger.warning("Fallback de IA indisponível (%s); mantendo extração determinística.", exc)
        if resultado is not None:
            return resultado
        raise

    if resultado is None or via_ia.confianca >= resultado.confianca:
        return via_ia
    return resultado


def _deterministico(doc, layouts) -> ResultadoExtracao | None:  # noqa: ANN001
    layout = detectar(doc, layouts)
    if layout is None:
        return None
    extrator = obter_extrator(layout.extrator_classe)
    if extrator is None:
        logger.warning(
            "Layout %s sem extrator registrado: %s", layout.codigo, layout.extrator_classe
        )
        return None
    resultado = extrator.extrair(doc)
    resultado.layout_codigo = layout.codigo
    return resultado
