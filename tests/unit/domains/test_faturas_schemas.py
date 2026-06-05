from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.app.core.enums import BaseLeitura, ModalidadeTarifaria, PostoHorario, TipoItem
from src.app.domains.faturas.schemas import FaturaCreate, ItemFaturaCreate, MedidaFaturaCreate


def test_fatura_competencia_deve_ser_yyyy_mm() -> None:
    with pytest.raises(ValidationError, match="YYYY-MM"):
        FaturaCreate(
            unidade_consumidora_id="00000000-0000-0000-0000-000000000001",
            competencia="2025-13",
            valor_total=Decimal("10"),
            modalidade=ModalidadeTarifaria.VERDE,
        )


def test_medida_nao_aceita_leitura_atual_menor() -> None:
    with pytest.raises(ValidationError, match="leitura_atual"):
        MedidaFaturaCreate(
            posto_horario=PostoHorario.UNICO,
            leitura_anterior=Decimal("100"),
            leitura_atual=Decimal("90"),
            consumo_kwh=Decimal("10"),
        )


def test_fatura_create_aceita_itens_aninhados() -> None:
    fatura = FaturaCreate(
        unidade_consumidora_id="00000000-0000-0000-0000-000000000001",
        competencia="2025-01",
        valor_total=Decimal("100"),
        modalidade=ModalidadeTarifaria.VERDE,
        base_leitura=BaseLeitura.REAL,
        itens=[
            ItemFaturaCreate(
                tipo_item=TipoItem.TUSD,
                descricao="TUSD consumo",
                quantidade=Decimal("100"),
                tarifa_unitaria=Decimal("1"),
                valor=Decimal("100"),
            )
        ],
    )

    assert fatura.competencia == "2025-01"
    assert fatura.itens[0].tipo_item == TipoItem.TUSD
