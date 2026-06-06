"""Modelo canônico de extração.

Representa o que foi lido de um arquivo bruto, *antes* da normalização para as
entidades de persistência (`Fatura`/`Medida`/`Item`/`Tributo`). Cada extração
carrega uma `confianca` agregada (0..1) que o pipeline usa para decidir se aciona
o fallback de IA.
"""

from decimal import Decimal

from pydantic import BaseModel, Field

from src.app.core.enums import (
    Bandeira,
    ModalidadeTarifaria,
    PostoHorario,
    Subgrupo,
    TipoItem,
    TipoTributo,
)


class ItemExtraido(BaseModel):
    tipo_item: TipoItem
    descricao: str
    quantidade: Decimal = Decimal("0")
    tarifa_unitaria: Decimal = Decimal("0")
    valor: Decimal
    base_icms: Decimal | None = None
    aliquota_icms: Decimal | None = None


class TributoExtraido(BaseModel):
    tipo_tributo: TipoTributo
    base_calculo: Decimal
    aliquota: Decimal
    valor: Decimal


class MedidaExtraida(BaseModel):
    serial_medidor: str | None = None
    posto_horario: PostoHorario = PostoHorario.UNICO
    leitura_anterior: Decimal = Decimal("0")
    leitura_atual: Decimal = Decimal("0")
    constante_medidor: Decimal = Decimal("1")
    consumo_kwh: Decimal = Decimal("0")


class FaturaExtraida(BaseModel):
    competencia: str = Field(description="Competência no formato YYYY-MM")
    numero_nota: str | None = None
    chave_acesso: str | None = None
    data_emissao: str | None = Field(default=None, description="Data ISO YYYY-MM-DD")
    data_vencimento: str | None = None
    data_leitura_anterior: str | None = None
    data_leitura_atual: str | None = None
    dias_faturados: int | None = None
    modalidade: ModalidadeTarifaria = ModalidadeTarifaria.CONVENCIONAL
    bandeira: Bandeira | None = None
    subgrupo: Subgrupo | None = None
    valor_total: Decimal
    itens: list[ItemExtraido] = Field(default_factory=list)
    tributos: list[TributoExtraido] = Field(default_factory=list)
    medidas: list[MedidaExtraida] = Field(default_factory=list)
    confianca: float = 1.0


class ResultadoExtracao(BaseModel):
    """Saída do pipeline: uma ou mais faturas (NF3e pode trazer N meses)."""

    faturas: list[FaturaExtraida] = Field(default_factory=list)
    metodo: str = "desconhecido"
    layout_codigo: str | None = None
    confianca: float = 0.0
