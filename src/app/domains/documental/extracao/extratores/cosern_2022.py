"""Extrator determinístico do layout Cosern 2022 ("DESCRIÇÃO DA NOTA FISCAL").

Usa o texto em modo *fluxo* (pdfplumber em ordem de leitura), no qual a tabela de
itens deste layout sai corretamente inline. Documento de página única = uma fatura.
"""

import re
from decimal import Decimal

from src.app.core.enums import TipoTributo
from src.app.domains.documental.extracao.base import (
    competencia_mm_aaaa,
    mapear_bandeira,
    mapear_modalidade,
    mapear_subgrupo,
    mapear_tipo_item,
    parse_data_br,
    parse_decimal_br,
    parse_int,
)
from src.app.domains.documental.extracao.schema import (
    FaturaExtraida,
    ItemExtraido,
    MedidaExtraida,
    ResultadoExtracao,
    TributoExtraido,
)
from src.app.domains.documental.extracao.texto import DocumentoTexto

DEC = r"[\d.]+,\d+"
TOLERANCIA = Decimal("0.05")

_LINHA_ITEM_QTD = re.compile(rf"^(.+?)\s+({DEC})\s+({DEC})\s+([\d.]+,\d{{2}})$")
_LINHA_ITEM_VALOR = re.compile(r"^(.+?)\s+([\d.]+,\d{2})$")
_MEDIDOR = re.compile(
    rf"(\d{{6,}})\s+\w+\s+(\d{{2}}/\d{{2}}/\d{{4}})\s+({DEC})\s+"
    rf"(\d{{2}}/\d{{2}}/\d{{4}})\s+({DEC})\s+(\d+)\s+({DEC})\s+([\d.]+,\d+)-?"
)


class CosernExtrator2022:
    codigo = "cosern_2022"

    def extrair(self, doc: DocumentoTexto) -> ResultadoExtracao:
        texto = doc.fluxo
        fatura = self._extrair_fatura(texto)
        return ResultadoExtracao(
            faturas=[fatura],
            metodo=f"deterministico:{self.codigo}",
            layout_codigo=self.codigo,
            confianca=fatura.confianca,
        )

    def _extrair_fatura(self, texto: str) -> FaturaExtraida:
        venc, emissao = self._datas_cabecalho(texto)
        leit_ant, leit_atual = self._datas_leitura(texto)
        itens = self._itens(texto)
        medidas = self._medidas(texto)
        valor_total = self._valor_total(texto)
        bandeira = next(
            (mapear_bandeira(i.descricao) for i in itens if "bandeira" in i.descricao.lower()),
            None,
        )
        subgrupo = mapear_subgrupo(self._classificacao(texto))
        fatura = FaturaExtraida(
            competencia=self._competencia(texto) or "1900-01",
            numero_nota=self._numero_nota(texto),
            data_emissao=emissao,
            data_vencimento=venc,
            data_leitura_anterior=leit_ant,
            data_leitura_atual=leit_atual,
            dias_faturados=self._dias(texto),
            modalidade=mapear_modalidade(self._tipo_fornecimento(texto)),
            bandeira=bandeira,
            subgrupo=subgrupo,
            valor_total=valor_total or Decimal("0"),
            itens=itens,
            tributos=self._tributos(texto),
            medidas=medidas,
        )
        fatura.confianca = self._confianca(fatura)
        return fatura

    def _datas_cabecalho(self, texto: str) -> tuple[str | None, str | None]:
        m = re.search(r"(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})\s+\d{7,}", texto)
        if not m:
            return None, None
        return parse_data_br(m.group(1)), parse_data_br(m.group(2))

    def _numero_nota(self, texto: str) -> str | None:
        m = re.search(r"(\d{6,})\s+N[ºo°]?\s*DA INSTALA", texto)
        return m.group(1) if m else None

    def _competencia(self, texto: str) -> str | None:
        # A competência aparece sob o rótulo "MÊS/ANO" (cabeçalho e talão de
        # pagamento). Ancorar nele evita capturar MM/AAAA de outras menções
        # (ex.: "Res. CREG 03/2021") ou o trecho embutido em datas DD/MM/AAAA.
        anchor = re.search(r"M[ÊE]S/ANO", texto)
        regiao = texto[anchor.end():] if anchor else texto
        m = re.search(r"(?<![\d/])(\d{2}/\d{4})(?![\d/])", regiao)
        return competencia_mm_aaaa(m.group(1)) if m else None

    def _classificacao(self, texto: str) -> str | None:
        m = re.search(
            r"\b([AB][S\da]{1,3})\s+(RESIDENCIAL|COMERCIAL|INDUSTRIAL|RURAL|PODER)", texto
        )
        return m.group(0) if m else None

    def _tipo_fornecimento(self, texto: str) -> str | None:
        m = re.search(r"(Conv\.|Bin[oô]mia|Mon[oô]mia|Branca|Azul|Verde)[^\n]*", texto)
        return m.group(0) if m else None

    def _dias(self, texto: str) -> int | None:
        m = _MEDIDOR.search(texto)
        return parse_int(m.group(6)) if m else None

    def _datas_leitura(self, texto: str) -> tuple[str | None, str | None]:
        m = _MEDIDOR.search(texto)
        if not m:
            return None, None
        return parse_data_br(m.group(2)), parse_data_br(m.group(4))

    def _valor_total(self, texto: str) -> Decimal | None:
        m = re.search(r"TOTAL DA FATURA\s+([\d.]+,\d{2})", texto)
        return parse_decimal_br(m.group(1)) if m else None

    def _itens(self, texto: str) -> list[ItemExtraido]:
        bloco = self._bloco(
            texto, r"DESCRI[ÇC][ÃA]O DA NOTA FISCAL", r"Tarifas Aplicadas|TOTAL DA FATURA"
        )
        itens: list[ItemExtraido] = []
        for linha in bloco.splitlines():
            linha = linha.strip()
            if not linha or "QUANTIDADE" in linha.upper() or "VALOR" in linha.upper():
                continue
            m = _LINHA_ITEM_QTD.match(linha)
            if m:
                desc, qtd, preco, valor = m.groups()
                itens.append(self._item(desc, valor, qtd, preco))
                continue
            m = _LINHA_ITEM_VALOR.match(linha)
            if m and re.search(r"[A-Za-z]", m.group(1)):
                desc, valor = m.groups()
                itens.append(self._item(desc, valor))
        return itens

    def _item(
        self, desc: str, valor: str, qtd: str | None = None, preco: str | None = None
    ) -> ItemExtraido:
        return ItemExtraido(
            tipo_item=mapear_tipo_item(desc),
            descricao=desc.strip(),
            quantidade=parse_decimal_br(qtd) or Decimal("0"),
            tarifa_unitaria=parse_decimal_br(preco) or Decimal("0"),
            valor=parse_decimal_br(valor) or Decimal("0"),
        )

    def _tributos(self, texto: str) -> list[TributoExtraido]:
        for linha in texto.splitlines():
            numeros = re.findall(DEC, linha)
            if len(numeros) >= 9 and "TOTAL" not in linha.upper():
                valores = [parse_decimal_br(n) for n in numeros[:9]]
                if any(v is None for v in valores):
                    continue
                ordem = [TipoTributo.ICMS, TipoTributo.PIS, TipoTributo.COFINS]
                return [
                    TributoExtraido(
                        tipo_tributo=tipo,
                        base_calculo=valores[i * 3],
                        aliquota=valores[i * 3 + 1],
                        valor=valores[i * 3 + 2],
                    )
                    for i, tipo in enumerate(ordem)
                ]
        return []

    def _medidas(self, texto: str) -> list[MedidaExtraida]:
        m = _MEDIDOR.search(texto)
        if not m:
            return []
        serial, _data_ant, leit_ant, _data_atual, leit_atual, _dias, const, consumo = m.groups()
        consumo_dec = parse_decimal_br(consumo) or Decimal("0")
        medida = MedidaExtraida(
            serial_medidor=serial,
            leitura_anterior=parse_decimal_br(leit_ant) or Decimal("0"),
            leitura_atual=parse_decimal_br(leit_atual) or Decimal("0"),
            constante_medidor=parse_decimal_br(const) or Decimal("1"),
            consumo_kwh=abs(consumo_dec),
        )
        return [medida]

    @staticmethod
    def _bloco(texto: str, inicio: str, fim: str) -> str:
        m_ini = re.search(inicio, texto)
        if not m_ini:
            return ""
        resto = texto[m_ini.end():]
        m_fim = re.search(fim, resto)
        return resto[: m_fim.start()] if m_fim else resto

    @staticmethod
    def _confianca(fatura: FaturaExtraida) -> float:
        score = 1.0
        if fatura.valor_total <= 0:
            score -= 0.4
        if not fatura.itens:
            score -= 0.3
        if not fatura.medidas:
            score -= 0.2
        if fatura.itens and fatura.valor_total > 0:
            soma = sum((i.valor for i in fatura.itens), Decimal("0"))
            if abs(soma - fatura.valor_total) > TOLERANCIA:
                score -= 0.2
        return round(max(score, 0.0), 2)
