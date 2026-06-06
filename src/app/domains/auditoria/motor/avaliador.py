"""Avaliador determinístico de regras DSL contra o contexto de uma fatura."""

from dataclasses import dataclass, field
from decimal import Decimal

from src.app.core.enums import ResultadoRegra as ResultadoRegraEnum
from src.app.domains.auditoria.motor.contexto import ContextoAvaliacao
from src.app.domains.auditoria.motor.dsl import RegraDSL
from src.app.domains.regulatorio.models import RegraValidacao

CENTAVO = Decimal("0.01")


@dataclass
class ResultadoAvaliacao:
    resultado: ResultadoRegraEnum
    mensagem: str
    valor_esperado: dict | None = None
    valor_encontrado: dict | None = None
    diferenca: dict | None = None
    cobrado_a_maior: Decimal = field(default_factory=lambda: Decimal("0"))


def avaliar(regra: RegraValidacao, ctx: ContextoAvaliacao) -> ResultadoAvaliacao:
    try:
        dsl = RegraDSL.model_validate(regra.expressao_logica or {})
    except Exception as exc:  # noqa: BLE001 - DSL malformada vira resultado de erro
        return ResultadoAvaliacao(
            resultado=ResultadoRegraEnum.ERRO,
            mensagem=f"Expressão lógica inválida em {regra.codigo}: {exc}",
        )

    despacho = {
        "recalculo_consumo": _recalculo_consumo,
        "valor_item_por_tarifa": _valor_item_por_tarifa,
        "soma_itens_total": _soma_itens_total,
    }
    return despacho[dsl.tipo](dsl, ctx)


def _recalculo_consumo(dsl: RegraDSL, ctx: ContextoAvaliacao) -> ResultadoAvaliacao:
    if not ctx.medidas:
        return _nao_aplicavel("Sem medidas para recalcular o consumo.")
    esperado = sum(
        ((m.leitura_atual - m.leitura_anterior) * m.constante_medidor for m in ctx.medidas),
        Decimal("0"),
    )
    encontrado = sum((m.consumo_kwh for m in ctx.medidas), Decimal("0"))
    diferenca = encontrado - esperado
    if abs(diferenca) <= dsl.tolerancia:
        return _passou("Consumo confere com as leituras.")
    return ResultadoAvaliacao(
        resultado=ResultadoRegraEnum.FALHOU,
        mensagem=(
            f"Consumo faturado ({encontrado} kWh) diverge do recalculado pelas leituras "
            f"({esperado} kWh)."
        ),
        valor_esperado={"consumo_kwh": str(esperado)},
        valor_encontrado={"consumo_kwh": str(encontrado)},
        diferenca={"consumo_kwh": str(diferenca)},
    )


def _valor_item_por_tarifa(dsl: RegraDSL, ctx: ContextoAvaliacao) -> ResultadoAvaliacao:
    if dsl.tipo_item is None or dsl.campo_snapshot is None:
        return _nao_aplicavel("Regra sem tipo_item/campo_snapshot.")
    if ctx.snapshot is None:
        return _nao_aplicavel("Sem snapshot tarifário vigente para a competência.")
    tarifa = getattr(ctx.snapshot, dsl.campo_snapshot, None)
    if tarifa is None:
        return _nao_aplicavel(f"Snapshot sem o campo {dsl.campo_snapshot}.")

    itens = ctx.itens_do_tipo(dsl.tipo_item)
    if not itens:
        return _nao_aplicavel(f"Fatura sem itens do tipo {dsl.tipo_item.value}.")

    esperado = sum((i.quantidade * tarifa for i in itens), Decimal("0")).quantize(CENTAVO)
    encontrado = sum((i.valor for i in itens), Decimal("0")).quantize(CENTAVO)
    diferenca = encontrado - esperado
    if abs(diferenca) <= dsl.tolerancia:
        return _passou(f"Valor de {dsl.tipo_item.value} confere com a tarifa vigente.")
    return ResultadoAvaliacao(
        resultado=ResultadoRegraEnum.FALHOU,
        mensagem=(
            f"Valor de {dsl.tipo_item.value} cobrado (R$ {encontrado}) diverge do esperado "
            f"(R$ {esperado}) pela tarifa {dsl.campo_snapshot}={tarifa}."
        ),
        valor_esperado={"valor": str(esperado), "tarifa": str(tarifa)},
        valor_encontrado={"valor": str(encontrado)},
        diferenca={"valor": str(diferenca)},
        cobrado_a_maior=max(diferenca, Decimal("0")),
    )


def _soma_itens_total(dsl: RegraDSL, ctx: ContextoAvaliacao) -> ResultadoAvaliacao:
    if not ctx.itens:
        return _nao_aplicavel("Fatura sem itens para somar.")
    encontrado = sum((i.valor for i in ctx.itens), Decimal("0")).quantize(CENTAVO)
    esperado = ctx.valor_total.quantize(CENTAVO)
    diferenca = encontrado - esperado
    if abs(diferenca) <= dsl.tolerancia:
        return _passou("Soma dos itens confere com o valor total.")
    return ResultadoAvaliacao(
        resultado=ResultadoRegraEnum.FALHOU,
        mensagem=(
            f"Soma dos itens (R$ {encontrado}) diverge do valor total da fatura "
            f"(R$ {esperado})."
        ),
        valor_esperado={"valor": str(esperado)},
        valor_encontrado={"valor": str(encontrado)},
        diferenca={"valor": str(diferenca)},
        cobrado_a_maior=max(diferenca, Decimal("0")),
    )


def _passou(mensagem: str) -> ResultadoAvaliacao:
    return ResultadoAvaliacao(resultado=ResultadoRegraEnum.PASSOU, mensagem=mensagem)


def _nao_aplicavel(mensagem: str) -> ResultadoAvaliacao:
    return ResultadoAvaliacao(resultado=ResultadoRegraEnum.NAO_APLICAVEL, mensagem=mensagem)
