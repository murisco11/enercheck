"""Contexto de avaliação: os dados da fatura + o snapshot tarifário vigente."""

from dataclasses import dataclass
from decimal import Decimal

from src.app.domains.faturas.models import Fatura, ItemFatura, MedidaFatura, TributoFatura
from src.app.domains.regulatorio.models import SnapshotTarifa


@dataclass(frozen=True)
class ContextoAvaliacao:
    fatura: Fatura
    medidas: list[MedidaFatura]
    itens: list[ItemFatura]
    tributos: list[TributoFatura]
    snapshot: SnapshotTarifa | None

    @property
    def valor_total(self) -> Decimal:
        return self.fatura.valor_total

    def itens_do_tipo(self, tipo) -> list[ItemFatura]:  # noqa: ANN001 - TipoItem
        return [i for i in self.itens if i.tipo_item == tipo]
