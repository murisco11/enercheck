"""Testes do motor determinístico: avaliador DSL e motor econômico."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from src.app.core.enums import PostoHorario, ResultadoRegra, TipoItem
from src.app.domains.auditoria.motor.avaliador import ResultadoAvaliacao, avaliar
from src.app.domains.auditoria.motor.contexto import ContextoAvaliacao
from src.app.domains.auditoria.motor.economico import quantificar
from src.app.domains.regulatorio.enums import CategoriaRegra


def _medida(ant, atual, const, consumo):
    return SimpleNamespace(
        leitura_anterior=Decimal(ant),
        leitura_atual=Decimal(atual),
        constante_medidor=Decimal(const),
        consumo_kwh=Decimal(consumo),
        posto_horario=PostoHorario.UNICO,
    )


def _item(tipo, qtd, tarifa, valor):
    return SimpleNamespace(
        tipo_item=tipo,
        quantidade=Decimal(qtd),
        tarifa_unitaria=Decimal(tarifa),
        valor=Decimal(valor),
    )


def _contexto(*, medidas=None, itens=None, snapshot=None, valor_total="0"):
    fatura = SimpleNamespace(valor_total=Decimal(valor_total), competencia="2025-01")
    return ContextoAvaliacao(
        fatura=fatura,
        medidas=medidas or [],
        itens=itens or [],
        tributos=[],
        snapshot=snapshot,
    )


def _regra(expressao):
    return SimpleNamespace(codigo="R", expressao_logica=expressao)


class TestRecalculoConsumo:
    def test_consumo_confere(self):
        ctx = _contexto(medidas=[_medida("100", "200", "1", "100")])
        r = avaliar(_regra({"tipo": "recalculo_consumo", "tolerancia": "0.01"}), ctx)
        assert r.resultado == ResultadoRegra.PASSOU

    def test_consumo_diverge(self):
        ctx = _contexto(medidas=[_medida("100", "200", "1", "150")])
        r = avaliar(_regra({"tipo": "recalculo_consumo", "tolerancia": "0.01"}), ctx)
        assert r.resultado == ResultadoRegra.FALHOU
        assert r.diferenca == {"consumo_kwh": "50"}

    def test_sem_medidas_nao_aplicavel(self):
        r = avaliar(_regra({"tipo": "recalculo_consumo"}), _contexto())
        assert r.resultado == ResultadoRegra.NAO_APLICAVEL


class TestValorItemPorTarifa:
    def _regra_tusd(self):
        return _regra(
            {
                "tipo": "valor_item_por_tarifa",
                "tipo_item": "tusd",
                "campo_snapshot": "valor_tusd_com_tributos",
                "tolerancia": "0.50",
            }
        )

    def test_valor_confere(self):
        snap = SimpleNamespace(valor_tusd_com_tributos=Decimal("0.40"))
        ctx = _contexto(itens=[_item(TipoItem.TUSD, "100", "0.40", "40.00")], snapshot=snap)
        r = avaliar(self._regra_tusd(), ctx)
        assert r.resultado == ResultadoRegra.PASSOU

    def test_cobranca_a_maior(self):
        snap = SimpleNamespace(valor_tusd_com_tributos=Decimal("0.40"))
        ctx = _contexto(itens=[_item(TipoItem.TUSD, "100", "0.50", "50.00")], snapshot=snap)
        r = avaliar(self._regra_tusd(), ctx)
        assert r.resultado == ResultadoRegra.FALHOU
        assert r.cobrado_a_maior == Decimal("10.00")

    def test_sem_snapshot_nao_aplicavel(self):
        ctx = _contexto(itens=[_item(TipoItem.TUSD, "100", "0.50", "50.00")], snapshot=None)
        r = avaliar(self._regra_tusd(), ctx)
        assert r.resultado == ResultadoRegra.NAO_APLICAVEL


class TestSomaItensTotal:
    def test_soma_confere(self):
        ctx = _contexto(
            itens=[_item(TipoItem.TUSD, "0", "0", "40.00"), _item(TipoItem.TE, "0", "0", "58.84")],
            valor_total="98.84",
        )
        r = avaliar(_regra({"tipo": "soma_itens_total", "tolerancia": "0.01"}), ctx)
        assert r.resultado == ResultadoRegra.PASSOU

    def test_dsl_invalida_vira_erro(self):
        r = avaliar(_regra({"tipo": "inexistente"}), _contexto())
        assert r.resultado == ResultadoRegra.ERRO


class TestMotorEconomico:
    def _avaliacao(self, valor):
        return ResultadoAvaliacao(
            resultado=ResultadoRegra.FALHOU, mensagem="x", cobrado_a_maior=Decimal(valor)
        )

    def test_cobranca_indevida_em_dobro_com_correcao(self):
        fatura = SimpleNamespace(competencia="2024-12")
        r = quantificar(
            self._avaliacao("10.00"),
            fatura,
            categoria=CategoriaRegra.COBRANCA_INDEVIDA,
            indice_mensal=Decimal("0.01"),
            referencia=date(2025, 12, 1),
        )
        assert r.valor_cobrado_a_maior == Decimal("10.00")
        assert r.correcao_monetaria == Decimal("1.20")  # 1% * 12 meses
        assert r.em_dobro is True
        assert r.valor_recuperavel == Decimal("22.40")

    def test_tarifa_devolucao_simples_sem_correcao(self):
        fatura = SimpleNamespace(competencia="2025-01")
        r = quantificar(
            self._avaliacao("10.00"),
            fatura,
            categoria=CategoriaRegra.TARIFA,
            indice_mensal=Decimal("0"),
            referencia=date(2025, 6, 1),
        )
        assert r.em_dobro is False
        assert r.valor_recuperavel == Decimal("10.00")

    def test_sem_cobranca_a_maior_nao_devolve(self):
        fatura = SimpleNamespace(competencia="2025-01")
        r = quantificar(self._avaliacao("0"), fatura, categoria=CategoriaRegra.TARIFA)
        assert r.valor_recuperavel == Decimal("0")
        assert r.modo_devolucao is None
