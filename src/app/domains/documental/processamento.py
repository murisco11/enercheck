"""Processamento assíncrono de um documento bruto: extração + normalização.

Executado via BackgroundTasks, portanto abre a própria sessão de banco (a sessão da
requisição já terá sido encerrada). Cada fatura é persistida em um savepoint: uma
chave de acesso duplicada apenas pula aquela fatura, sem abortar o lote.
"""

import logging
import uuid

from sqlalchemy.exc import IntegrityError

from src.app.api.v1.dependencies import get_session_manager
from src.app.core.enums import StatusExtracao
from src.app.core.storage import get_object_storage
from src.app.domains.clientes.repository import UnidadeConsumidoraRepository
from src.app.domains.documental.extracao import executar_extracao
from src.app.domains.documental.normalizacao import para_fatura_create
from src.app.domains.documental.repository import (
    DocumentoBrutoRepository,
    LayoutFaturaRepository,
)
from src.app.domains.faturas.repository import FaturaRepository

logger = logging.getLogger(__name__)


def processar_extracao(documento_id: uuid.UUID) -> None:
    manager = get_session_manager()
    with manager.session_factory() as db:
        documento = DocumentoBrutoRepository(db).buscar_por_id(documento_id)
        if documento is None:
            logger.warning("Documento %s não encontrado para extração.", documento_id)
            return

        documento.status_extracao = StatusExtracao.PROCESSANDO
        db.commit()

        try:
            uc = UnidadeConsumidoraRepository(db).buscar_por_id(documento.unidade_consumidora_id)
            if uc is None:
                raise ValueError("Unidade consumidora do documento não encontrada.")

            layouts = LayoutFaturaRepository(db).listar(uc.distribuidora_id)
            conteudo = get_object_storage().ler(documento.uri_armazenamento)
            resultado = executar_extracao(conteudo, layouts)

            persistidas = _persistir_faturas(db, documento, uc.id, resultado.faturas)
            documento.payload_extracao = {
                "extracao": resultado.model_dump(mode="json"),
                "faturas_detectadas": len(resultado.faturas),
                "faturas_persistidas": persistidas,
            }
            documento.status_extracao = StatusExtracao.CONCLUIDO
            documento.erro_extracao = None
            db.commit()
            logger.info(
                "Extração do documento %s concluída: %s/%s faturas persistidas (%s).",
                documento_id, persistidas, len(resultado.faturas), resultado.metodo,
            )
        except Exception as exc:  # noqa: BLE001 - registra o erro no próprio documento
            db.rollback()
            documento = DocumentoBrutoRepository(db).buscar_por_id(documento_id)
            if documento is not None:
                documento.status_extracao = StatusExtracao.ERRO
                documento.erro_extracao = str(exc)[:2000]
                db.commit()
            logger.exception("Falha na extração do documento %s", documento_id)


def _persistir_faturas(db, documento, uc_id, faturas) -> int:  # noqa: ANN001
    repo = FaturaRepository(db)
    persistidas = 0
    for extraida in faturas:
        dados = para_fatura_create(
            extraida,
            unidade_consumidora_id=uc_id,
            documento_bruto_id=documento.id,
            lote_auditoria_id=documento.lote_auditoria_id,
        )
        try:
            with db.begin_nested():
                repo.criar(dados)
            persistidas += 1
        except IntegrityError:
            # Chave de acesso já existente: duplicata exata, ignorada.
            logger.info("Fatura %s já existe (chave duplicada); ignorada.", extraida.chave_acesso)
    return persistidas
