"""Contrato dos extratores determinísticos e utilitários de parsing BR."""

import re
from decimal import Decimal, InvalidOperation
from typing import Protocol

from src.app.core.enums import Bandeira, ModalidadeTarifaria, Subgrupo, TipoItem
from src.app.domains.documental.extracao.schema import ResultadoExtracao
from src.app.domains.documental.extracao.texto import DocumentoTexto

MESES_PT = {
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
}


class Extrator(Protocol):
    codigo: str

    def extrair(self, doc: DocumentoTexto) -> ResultadoExtracao: ...


def parse_decimal_br(valor: str | None) -> Decimal | None:
    """Converte '1.234,56' ou '0,40867741' em Decimal. Trata sufixo de sinal '-'."""
    if valor is None:
        return None
    bruto = valor.strip()
    if not bruto:
        return None
    negativo = bruto.endswith("-")
    bruto = bruto.rstrip("-").strip()
    bruto = bruto.replace(".", "").replace(",", ".")
    try:
        numero = Decimal(bruto)
    except InvalidOperation:
        return None
    return -numero if negativo else numero


def parse_int(valor: str | None) -> int | None:
    if valor is None:
        return None
    digitos = re.sub(r"\D", "", valor)
    return int(digitos) if digitos else None


def parse_data_br(valor: str | None) -> str | None:
    """'05/01/2022' -> '2022-01-05' (ISO)."""
    if valor is None:
        return None
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", valor)
    if not m:
        return None
    dia, mes, ano = m.groups()
    return f"{ano}-{mes}-{dia}"


def competencia_mm_aaaa(valor: str | None) -> str | None:
    """'12/2021' -> '2021-12'."""
    if valor is None:
        return None
    m = re.search(r"(\d{2})/(\d{4})", valor)
    if not m:
        return None
    mes, ano = m.groups()
    return f"{ano}-{mes}"


def normalizar_chave(valor: str | None) -> str | None:
    if valor is None:
        return None
    digitos = re.sub(r"\D", "", valor)
    return digitos if len(digitos) == 44 else None


def mapear_subgrupo(classificacao: str | None) -> Subgrupo | None:
    if not classificacao:
        return None
    texto = classificacao.upper()
    for sub in Subgrupo:
        if re.search(rf"\b{sub.value}\b", texto):
            return sub
    return None


def mapear_modalidade(texto: str | None) -> ModalidadeTarifaria:
    if not texto:
        return ModalidadeTarifaria.CONVENCIONAL
    t = texto.lower()
    if "azul" in t:
        return ModalidadeTarifaria.AZUL
    if "verde" in t:
        return ModalidadeTarifaria.VERDE
    if "branca" in t:
        return ModalidadeTarifaria.BRANCA
    return ModalidadeTarifaria.CONVENCIONAL


def mapear_bandeira(descricao: str | None) -> Bandeira | None:
    if not descricao:
        return None
    d = descricao.lower()
    if "escassez" in d:
        return Bandeira.ESCASSEZ
    if "verde" in d:
        return Bandeira.VERDE
    if "amarela" in d:
        return Bandeira.AMARELA
    if "vermelha" in d:
        return Bandeira.VERMELHA_2 if ("2" in d or "patamar 2" in d) else Bandeira.VERMELHA_1
    return None


def mapear_tipo_item(descricao: str) -> TipoItem:
    d = descricao.lower()
    if "tusd" in d:
        return TipoItem.TUSD
    if "-te" in d or " te" in d or d.endswith("te"):
        return TipoItem.TE
    if "demanda" in d:
        return TipoItem.DEMANDA
    if "bandeira" in d or "band." in d or "band " in d:
        return TipoItem.BANDEIRA
    if "ilum" in d or "cosip" in d or "cip" in d:
        return TipoItem.COSIP
    if "multa" in d:
        return TipoItem.MULTA
    if "juros" in d:
        return TipoItem.JUROS
    if "desconto" in d or "credito" in d or "crédito" in d:
        return TipoItem.DESCONTO
    return TipoItem.OUTRO
