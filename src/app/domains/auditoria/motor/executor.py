"""Executor do motor de validação.

Resolve o contexto regulatório, avalia cada regra aplicável contra a fatura e
materializa a ExecucaoValidacao, os ResultadoRegra e os Achados. É aqui que a
divergência técnica vira achado quantificado — sempre de forma determinística.
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from src.app.core.enums import ResultadoRegra as ResultadoRegraEnum
from src.app.core.enums import StatusAchado, StatusExecucao
from src.app.core.exceptions import NaoEncontradoError
from src.app.domains.auditoria.models import Achado, ExecucaoValidacao, ResultadoRegra
from src.app.domains.auditoria.motor.avaliador import ResultadoAvaliacao, avaliar
from src.app.domains.auditoria.motor.contexto import ContextoAvaliacao
from src.app.domains.clientes.repository import UnidadeConsumidoraRepository
from src.app.domains.faturas.models import Fatura
from src.app.domains.faturas.repository import FaturaRepository
from src.app.domains.regulatorio.service import ContextoRegulatorio, ResolucaoService


class ValidacaoExecutor:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.fatura_repo = FaturaRepository(db)
        self.uc_repo = UnidadeConsumidoraRepository(db)
        self.resolucao = ResolucaoService(db)

    def executar(self, fatura_id: uuid.UUID, disparado_por_id: uuid.UUID) -> ExecucaoValidacao:
        fatura = self.fatura_repo.buscar_por_id(fatura_id, detalhe=True)
        if fatura is None:
            raise NaoEncontradoError("Fatura não encontrada.")
        uc = self.uc_repo.buscar_por_id(fatura.unidade_consumidora_id)
        if uc is None:
            raise NaoEncontradoError("Unidade consumidora não encontrada.")

        contexto_reg = self.resolucao.resolver_contexto(
            distribuidora_id=uc.distribuidora_id,
            grupo=uc.grupo,
            subgrupo=uc.subgrupo,
            modalidade=fatura.modalidade,
            competencia=fatura.competencia,
            posto=fatura.medidas[0].posto_horario if len(fatura.medidas) == 1 else None,
        )

        execucao = ExecucaoValidacao(
            fatura_id=fatura.id,
            pacote_regras_id=contexto_reg.pacote.id,
            snapshot_tarifa_id=contexto_reg.snapshot.id if contexto_reg.snapshot else None,
            disparado_por_id=disparado_por_id,
            status=StatusExecucao.PROCESSANDO,
        )
        self.db.add(execucao)
        self.db.flush()

        ctx = self._contexto(fatura, contexto_reg)
        total_avaliadas, total_achados, total_valor = self._avaliar_regras(
            fatura, execucao, contexto_reg, ctx
        )

        execucao.total_regras_avaliadas = total_avaliadas
        execucao.total_achados = total_achados
        execucao.valor_total_cobrado_a_maior = total_valor
        execucao.status = StatusExecucao.CONCLUIDO
        execucao.finalizado_em = datetime.now(UTC)
        self.db.flush()
        return execucao

    def _avaliar_regras(
        self,
        fatura: Fatura,
        execucao: ExecucaoValidacao,
        contexto_reg: ContextoRegulatorio,
        ctx: ContextoAvaliacao,
    ) -> tuple[int, int, Decimal]:
        total_avaliadas = 0
        total_achados = 0
        total_valor = Decimal("0")
        for regra in contexto_reg.regras:
            avaliacao = avaliar(regra, ctx)
            total_avaliadas += 1
            resultado = self._gravar_resultado(execucao, regra, avaliacao)
            if avaliacao.resultado == ResultadoRegraEnum.FALHOU:
                achado = self._gravar_achado(fatura, execucao, regra, resultado, avaliacao)
                total_achados += 1
                total_valor += achado.valor_cobrado_a_maior
        return total_avaliadas, total_achados, total_valor

    def _gravar_resultado(
        self, execucao: ExecucaoValidacao, regra, avaliacao: ResultadoAvaliacao
    ) -> ResultadoRegra:
        resultado = ResultadoRegra(
            execucao_validacao_id=execucao.id,
            regra_validacao_id=regra.id,
            resultado=avaliacao.resultado,
            valor_esperado=avaliacao.valor_esperado,
            valor_encontrado=avaliacao.valor_encontrado,
            diferenca=avaliacao.diferenca,
            severidade=regra.severidade,
            mensagem=avaliacao.mensagem,
        )
        self.db.add(resultado)
        self.db.flush()
        return resultado

    def _gravar_achado(
        self,
        fatura: Fatura,
        execucao: ExecucaoValidacao,
        regra,
        resultado: ResultadoRegra,
        avaliacao: ResultadoAvaliacao,
    ) -> Achado:
        # A quantificação econômica (atualização monetária, devolução em dobro) é
        # aplicada na Fase 5; por ora usa-se o valor cru apurado pela regra.
        valor, modo = avaliacao.cobrado_a_maior, None
        achado = Achado(
            fatura_id=fatura.id,
            execucao_validacao_id=execucao.id,
            resultado_regra_id=resultado.id,
            titulo=regra.nome,
            descricao=avaliacao.mensagem,
            categoria=regra.categoria,
            severidade=regra.severidade,
            status=StatusAchado.ABERTO,
            valor_cobrado_a_maior=valor,
            modo_devolucao_estimado=modo,
        )
        self.db.add(achado)
        self.db.flush()
        return achado

    @staticmethod
    def _contexto(fatura: Fatura, contexto_reg: ContextoRegulatorio) -> ContextoAvaliacao:
        return ContextoAvaliacao(
            fatura=fatura,
            medidas=list(fatura.medidas),
            itens=list(fatura.itens),
            tributos=list(fatura.tributos),
            snapshot=contexto_reg.snapshot,
        )
