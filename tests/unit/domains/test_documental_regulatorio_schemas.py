from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.app.core.enums import Grupo, ModalidadeTarifaria, Subgrupo
from src.app.domains.documental.schemas import DocumentoBrutoCreate, LayoutFaturaCreate
from src.app.domains.regulatorio.enums import OrigemRegulatoria, TipoDocumento
from src.app.domains.regulatorio.schemas import DocumentoRegulatorioCreate, SnapshotTarifaCreate

UUID_1 = "00000000-0000-0000-0000-000000000001"


def test_documento_bruto_valida_sha256_hexadecimal() -> None:
    with pytest.raises(ValidationError, match="sha256"):
        DocumentoBrutoCreate(
            unidade_consumidora_id=UUID_1,
            uri_armazenamento="s3://bucket/doc.pdf",
            nome_original="doc.pdf",
            sha256="x" * 64,
        )


def test_layout_valida_ordem_de_vigencia() -> None:
    with pytest.raises(ValidationError, match="vigencia_fim"):
        LayoutFaturaCreate(
            distribuidora_id=UUID_1,
            codigo="LAYOUT-1",
            descricao="Layout teste",
            extrator_classe="ExtratorTeste",
            vigencia_inicio=date(2025, 2, 1),
            vigencia_fim=date(2025, 1, 1),
        )


def test_documento_regulatorio_valida_ordem_de_vigencia() -> None:
    with pytest.raises(ValidationError, match="vigencia_fim"):
        DocumentoRegulatorioCreate(
            identificador="REN-TESTE",
            titulo="Documento teste",
            origem=OrigemRegulatoria.ANEEL,
            tipo=TipoDocumento.RESOLUCAO_NORMATIVA,
            vigencia_inicio=date(2025, 2, 1),
            vigencia_fim=date(2025, 1, 1),
        )


def test_snapshot_tarifa_usa_decimal_e_valida_valores() -> None:
    snapshot = SnapshotTarifaCreate(
        distribuidora_id=UUID_1,
        grupo=Grupo.A,
        subgrupo=Subgrupo.A4,
        modalidade=ModalidadeTarifaria.VERDE,
        vigencia_inicio=date(2025, 1, 1),
        valor_tusd=Decimal("0.50"),
        valor_te=Decimal("0.30"),
        valor_tusd_com_tributos=Decimal("0.55"),
        valor_te_com_tributos=Decimal("0.35"),
    )

    assert snapshot.valor_tusd == Decimal("0.50")
