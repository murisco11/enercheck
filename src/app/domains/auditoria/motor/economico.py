"""Motor econômico: transforma a divergência técnica em valor recuperável.

Aplica atualização monetária parametrizada sobre o valor cobrado a maior e faz a
classificação preliminar entre devolução simples e em dobro (REN 1.000/2021,
art. 113: a cobrança indevida é restituída em dobro, salvo engano justificável).

Permanece determinístico: a IA não origina valor.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal

from src.app.core.config import get_settings
from src.app.core.enums import ModoDevolucao
from src.app.domains.auditoria.motor.avaliador import ResultadoAvaliacao
from src.app.domains.faturas.models import Fatura
from src.app.domains.regulatorio.enums import CategoriaRegra

CENTAVO = Decimal("0.01")


@dataclass(frozen=True)
class ResultadoEconomico:
    valor_cobrado_a_maior: Decimal
    correcao_monetaria: Decimal
    valor_atualizado: Decimal
    em_dobro: bool
    valor_recuperavel: Decimal
    modo_devolucao: ModoDevolucao | None


def quantificar(
    avaliacao: ResultadoAvaliacao,
    fatura: Fatura,
    *,
    categoria: CategoriaRegra,
    indice_mensal: Decimal | None = None,
    referencia: date | None = None,
) -> ResultadoEconomico:
    base = avaliacao.cobrado_a_maior.quantize(CENTAVO)
    if base <= 0:
        return ResultadoEconomico(
            valor_cobrado_a_maior=base,
            correcao_monetaria=Decimal("0.00"),
            valor_atualizado=base,
            em_dobro=False,
            valor_recuperavel=base,
            modo_devolucao=None,
        )

    indice = (
        Decimal(str(get_settings().economico_indice_mensal))
        if indice_mensal is None
        else indice_mensal
    )
    hoje = referencia or datetime.now(UTC).date()
    meses = _meses_decorridos(fatura.competencia, hoje)
    valor_atualizado = (base * (Decimal("1") + indice * meses)).quantize(
        CENTAVO, rounding=ROUND_HALF_UP
    )
    correcao = valor_atualizado - base

    em_dobro = categoria == CategoriaRegra.COBRANCA_INDEVIDA
    multiplicador = Decimal("2") if em_dobro else Decimal("1")
    valor_recuperavel = (valor_atualizado * multiplicador).quantize(CENTAVO)

    return ResultadoEconomico(
        valor_cobrado_a_maior=base,
        correcao_monetaria=correcao,
        valor_atualizado=valor_atualizado,
        em_dobro=em_dobro,
        valor_recuperavel=valor_recuperavel,
        modo_devolucao=ModoDevolucao.CREDITO_FATURA,
    )


def _meses_decorridos(competencia: str, hoje: date) -> Decimal:
    try:
        ano, mes = (int(p) for p in competencia.split("-"))
    except (ValueError, AttributeError):
        return Decimal("0")
    meses = (hoje.year - ano) * 12 + (hoje.month - mes)
    return Decimal(max(meses, 0))
