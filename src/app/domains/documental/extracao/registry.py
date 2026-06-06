"""Registro de extratores determinísticos, indexados por `LayoutFatura.extrator_classe`."""

from src.app.domains.documental.extracao.base import Extrator
from src.app.domains.documental.extracao.extratores.cosern_2022 import CosernExtrator2022
from src.app.domains.documental.extracao.extratores.cosern_nf3e import CosernExtratorNF3e

_EXTRATORES: dict[str, Extrator] = {
    CosernExtrator2022.codigo: CosernExtrator2022(),
    CosernExtratorNF3e.codigo: CosernExtratorNF3e(),
}


def obter_extrator(codigo: str) -> Extrator | None:
    return _EXTRATORES.get(codigo)


def codigos_disponiveis() -> list[str]:
    return sorted(_EXTRATORES)
