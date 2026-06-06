"""Detecção de duplicidade lógica de faturas.

A duplicata *exata* (mesmo arquivo via sha256; mesma chave de acesso NF3e) já é
bloqueada na ingestão/persistência. Aqui tratamos a duplicata *lógica* — mesma
unidade consumidora + competência, ou mesmo número de nota — que não é bloqueada:
gera-se um Achado de categoria DUPLICIDADE para que o revisor decida.
"""

import logging

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from src.app.core.enums import StatusAchado
from src.app.domains.auditoria.models import Achado
from src.app.domains.faturas.models import Fatura
from src.app.domains.regulatorio.enums import CategoriaRegra, Severidade

logger = logging.getLogger(__name__)


def sinalizar_duplicidade(db: Session, fatura: Fatura) -> Achado | None:
    """Cria um achado se a fatura recém-persistida duplicar logicamente outra."""
    criterios = [
        and_(
            Fatura.unidade_consumidora_id == fatura.unidade_consumidora_id,
            Fatura.competencia == fatura.competencia,
        )
    ]
    if fatura.numero_nota:
        criterios.append(Fatura.numero_nota == fatura.numero_nota)

    stmt = (
        select(Fatura)
        .where(Fatura.id != fatura.id)
        .where(or_(*criterios))
        .limit(1)
    )
    existente = db.scalar(stmt)
    if existente is None:
        return None

    achado = Achado(
        fatura_id=fatura.id,
        titulo="Possível fatura duplicada",
        descricao=(
            f"A fatura da competência {fatura.competencia} desta unidade consumidora "
            f"coincide com a fatura {existente.id} (mesma competência/UC ou número de "
            f"nota {fatura.numero_nota}). Verifique se houve reenvio ou refaturamento."
        ),
        categoria=CategoriaRegra.DUPLICIDADE,
        severidade=Severidade.MEDIA,
        status=StatusAchado.ABERTO,
    )
    db.add(achado)
    db.flush()
    logger.info("Duplicidade sinalizada: fatura %s ~ %s", fatura.id, existente.id)
    return achado
