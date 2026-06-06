"""Validação de um lote inteiro em background.

Percorre todas as faturas do lote e roda o motor determinístico em cada uma,
isolando falhas por fatura (uma execução com erro não aborta o lote). Atualiza o
status do LoteAuditoria ao final.
"""

import logging
import uuid

from src.app.api.v1.dependencies import get_session_manager
from src.app.core.enums import StatusLote
from src.app.domains.auditoria.motor import ValidacaoExecutor
from src.app.domains.clientes.repository import LoteRepository
from src.app.domains.faturas.repository import FaturaRepository

logger = logging.getLogger(__name__)


def processar_validacao_lote(lote_id: uuid.UUID, disparado_por_id: uuid.UUID) -> None:
    manager = get_session_manager()
    with manager.session_factory() as db:
        lote = LoteRepository(db).buscar_por_id(lote_id)
        if lote is None:
            logger.warning("Lote %s não encontrado para validação.", lote_id)
            return

        lote.status = StatusLote.PROCESSANDO
        db.commit()

        faturas = FaturaRepository(db).listar(lote_auditoria_id=lote_id)
        executor = ValidacaoExecutor(db)
        houve_erro = False
        for fatura in faturas:
            try:
                with db.begin_nested():
                    executor.executar(fatura.id, disparado_por_id=disparado_por_id)
            except Exception:  # noqa: BLE001 - isola a falha de uma fatura
                houve_erro = True
                logger.exception("Falha ao validar fatura %s do lote %s", fatura.id, lote_id)

        lote.status = StatusLote.ERRO if houve_erro else StatusLote.CONCLUIDO
        db.commit()
        logger.info(
            "Validação do lote %s concluída: %s faturas, status %s.",
            lote_id, len(faturas), lote.status,
        )
