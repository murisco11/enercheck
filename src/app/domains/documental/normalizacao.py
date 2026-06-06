"""Normalização: converte a extração canônica em `FaturaCreate` para persistência.

A reconciliação itens+tributos×total do `FaturaService` não se aplica aqui: em
faturas brasileiras os tributos (ICMS/PIS/COFINS) são destacados *dentro* do valor
dos itens, então a normalização persiste diretamente pelo repositório.
"""

import uuid

from src.app.domains.documental.extracao.schema import FaturaExtraida
from src.app.domains.faturas.schemas import (
    FaturaCreate,
    ItemFaturaCreate,
    MedidaFaturaCreate,
    TributoFaturaCreate,
)


def para_fatura_create(
    extraida: FaturaExtraida,
    *,
    unidade_consumidora_id: uuid.UUID,
    documento_bruto_id: uuid.UUID | None = None,
    lote_auditoria_id: uuid.UUID | None = None,
) -> FaturaCreate:
    return FaturaCreate(
        unidade_consumidora_id=unidade_consumidora_id,
        documento_bruto_id=documento_bruto_id,
        lote_auditoria_id=lote_auditoria_id,
        numero_nota=extraida.numero_nota,
        chave_acesso=extraida.chave_acesso,
        competencia=extraida.competencia,
        data_emissao=extraida.data_emissao,
        data_vencimento=extraida.data_vencimento,
        data_leitura_anterior=extraida.data_leitura_anterior,
        data_leitura_atual=extraida.data_leitura_atual,
        dias_faturados=extraida.dias_faturados,
        bandeira=extraida.bandeira,
        valor_total=extraida.valor_total,
        modalidade=extraida.modalidade,
        medidas=[
            MedidaFaturaCreate(
                serial_medidor=m.serial_medidor,
                posto_horario=m.posto_horario,
                leitura_anterior=m.leitura_anterior,
                leitura_atual=m.leitura_atual,
                constante_medidor=m.constante_medidor,
                consumo_kwh=m.consumo_kwh,
            )
            for m in extraida.medidas
        ],
        itens=[
            ItemFaturaCreate(
                tipo_item=i.tipo_item,
                descricao=i.descricao,
                quantidade=i.quantidade,
                tarifa_unitaria=i.tarifa_unitaria,
                valor=i.valor,
                base_icms=i.base_icms,
                aliquota_icms=i.aliquota_icms,
                ordem=ordem,
            )
            for ordem, i in enumerate(extraida.itens)
        ],
        tributos=[
            TributoFaturaCreate(
                tipo_tributo=t.tipo_tributo,
                base_calculo=t.base_calculo,
                aliquota=t.aliquota,
                valor=t.valor,
            )
            for t in extraida.tributos
        ],
    )
