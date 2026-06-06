"""Extrator determinístico do layout Cosern NF3e (DANFE, a partir de ~2024).

Usa o texto em modo *layout* (pdftotext -layout), no qual o cabeçalho e a tabela
de itens da NF3e ficam espacialmente recuperáveis. Um único arquivo costuma reunir
várias competências: cada página-frente que contém "ITENS DA FATURA" corresponde a
uma fatura. O valor de cada item é reconstruído por quantidade × tarifa unitária.
"""

import re
from decimal import Decimal

from src.app.core.enums import PostoHorario, TipoTributo
from src.app.domains.documental.extracao.base import (
    competencia_mm_aaaa,
    mapear_bandeira,
    mapear_modalidade,
    mapear_subgrupo,
    mapear_tipo_item,
    normalizar_chave,
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

CENTAVO = Decimal("0.01")
TOLERANCIA = Decimal("1.00")

_ITEM_CONSUMO = re.compile(r"^(Consumo-?\s?T[EU]S?D?|Consumo-?\s?TE)\b", re.I)
_QTD_PRECO = re.compile(r"(\d{1,3}(?:\.\d{3})*,\d{2})\s+(0,\d{6,})")
# Linha do medidor: nº de série + grandeza + posto (+ leituras/consumo, que podem
# estar na mesma linha ou na seguinte). O ^\s* tolera a indentação do pdfplumber.
_MEDIDOR = re.compile(r"^\s*(\d{8,})\b[^\n]*\b(Único|Ponta|Fora|Intermedi)[^\n]*", re.I | re.M)
_DEC = r"\d{1,3}(?:\.\d{3})*,\d+|\d+,\d+"
# Chave NF3e: 11 grupos de 4 dígitos (44 no total). Os lookarounds de dígito
# evitam capturar o fim de um número vizinho (ex.: código do cliente) como 1º grupo.
_CHAVE = re.compile(r"(?<!\d)((?:\d{4}\s+){10}\d{4})(?!\d)")
_BANDEIRA = re.compile(r"Band\.?\s*(VERMELHA|AMARELA|VERDE|ESCASSEZ)", re.I)


class CosernExtratorNF3e:
    codigo = "cosern_nf3e"

    def extrair(self, doc: DocumentoTexto) -> ResultadoExtracao:
        faturas = [
            self._extrair_fatura(pagina)
            for pagina in doc.paginas_layout
            if "ITENS DA FATURA" in pagina
        ]
        confianca = min((f.confianca for f in faturas), default=0.0)
        return ResultadoExtracao(
            faturas=faturas,
            metodo=f"deterministico:{self.codigo}",
            layout_codigo=self.codigo,
            confianca=confianca,
        )

    def _extrair_fatura(self, pagina: str) -> FaturaExtraida:
        itens = self._itens(pagina)
        medidas = self._medidas(pagina)
        bandeira = self._bandeira(pagina)
        fatura = FaturaExtraida(
            competencia=self._competencia(pagina) or "1900-01",
            numero_nota=self._numero_nota(pagina),
            chave_acesso=self._chave(pagina),
            data_emissao=self._emissao(pagina),
            data_vencimento=self._vencimento(pagina),
            data_leitura_anterior=self._campo_data(pagina, "LEITURA ANTERIOR"),
            data_leitura_atual=self._campo_data(pagina, "LEITURA ATUAL"),
            dias_faturados=self._dias(pagina),
            modalidade=mapear_modalidade(self._tipo_fornecimento(pagina)),
            bandeira=bandeira,
            subgrupo=mapear_subgrupo(self._classificacao(pagina)),
            valor_total=self._valor_total(pagina) or Decimal("0"),
            itens=itens,
            tributos=self._tributos(pagina),
            medidas=medidas,
        )
        fatura.confianca = self._confianca(fatura)
        return fatura

    def _numero_nota(self, t: str) -> str | None:
        m = re.search(r"NOTA FISCAL N[°ºo]?\s*(\d+)", t)
        return m.group(1) if m else None

    def _chave(self, t: str) -> str | None:
        m = _CHAVE.search(t)
        return normalizar_chave(m.group(1)) if m else None

    def _bandeira(self, t: str):  # noqa: ANN202 - retorna Bandeira | None
        m = _BANDEIRA.search(t)
        return mapear_bandeira(m.group(0)) if m else None

    def _emissao(self, t: str) -> str | None:
        m = re.search(r"DATA DE EMISS[ÃA]O:\s*(\d{2}/\d{2}/\d{4})", t)
        return parse_data_br(m.group(1)) if m else None

    def _vencimento(self, t: str) -> str | None:
        m = re.search(r"(?<!DATA DE )VENCIMENTO\s*\n+\s*(\d{2}/\d{2}/\d{4})", t)
        if m:
            return parse_data_br(m.group(1))
        m = re.search(r"VENCIMENTO[^\d]{0,40}(\d{2}/\d{2}/\d{4})", t)
        return parse_data_br(m.group(1)) if m else None

    def _campo_data(self, t: str, rotulo: str) -> str | None:
        m = re.search(rf"{rotulo}\s+(\d{{2}}/\d{{2}}/\d{{4}})", t)
        return parse_data_br(m.group(1)) if m else None

    def _dias(self, t: str) -> int | None:
        m = re.search(r"N[°ºo]?\s*DE DIAS\s+(\d+)", t)
        return parse_int(m.group(1)) if m else None

    def _competencia(self, t: str) -> str | None:
        anchor = re.search(r"M[ÊE]S/ANO", t)
        regiao = t[anchor.end():] if anchor else t
        m = re.search(r"(?<![\d/])(\d{2}/\d{4})(?![\d/])", regiao)
        return competencia_mm_aaaa(m.group(1)) if m else None

    def _classificacao(self, t: str) -> str | None:
        m = re.search(r"CLASSIFICA[ÇC][ÃA]O:\s*([^\n]+)", t)
        return m.group(1) if m else None

    def _tipo_fornecimento(self, t: str) -> str | None:
        m = re.search(r"TIPO DE FORNECIMENTO:\s*([^\n]+)", t)
        return m.group(1) if m else None

    def _valor_total(self, t: str) -> Decimal | None:
        m = re.search(r"^\s*TOTAL\s+([\d.]+,\d{2})", t, re.M)
        return parse_decimal_br(m.group(1)) if m else None

    def _itens(self, t: str) -> list[ItemExtraido]:
        itens: list[ItemExtraido] = []
        linhas = t.splitlines()
        for idx, linha in enumerate(linhas):
            if not _ITEM_CONSUMO.search(linha.strip()):
                continue
            descricao = re.split(r"\s{2,}|\bkWh\b", linha.strip())[0].strip()
            qtd_preco = self._qtd_preco_proximo(linhas, idx)
            if qtd_preco is None:
                continue
            quantidade, tarifa = qtd_preco
            valor = (quantidade * tarifa).quantize(CENTAVO)
            itens.append(
                ItemExtraido(
                    tipo_item=mapear_tipo_item(descricao),
                    descricao=descricao,
                    quantidade=quantidade,
                    tarifa_unitaria=tarifa,
                    valor=valor,
                )
            )
        return itens

    def _qtd_preco_proximo(
        self, linhas: list[str], idx: int
    ) -> tuple[Decimal, Decimal] | None:
        # Em algumas linhas a quantidade/tarifa do item ficam na própria linha; em
        # outras (Consumo-TE) deslocam para a linha imediatamente acima/abaixo.
        for offset in (0, -1, 1):
            alvo = idx + offset
            if 0 <= alvo < len(linhas):
                m = _QTD_PRECO.search(linhas[alvo])
                if m:
                    qtd = parse_decimal_br(m.group(1))
                    preco = parse_decimal_br(m.group(2))
                    if qtd is not None and preco is not None:
                        return qtd, preco
        return None

    def _tributos(self, t: str) -> list[TributoExtraido]:
        mapa = {"PIS": TipoTributo.PIS, "COFINS": TipoTributo.COFINS, "ICMS": TipoTributo.ICMS}
        tributos: list[TributoExtraido] = []
        for nome, tipo in mapa.items():
            m = re.search(rf"\b{nome}\s+([\d.]+,\d{{2}})\s+([\d.]+,\d{{2}})\s+([\d.]+,\d{{2}})", t)
            if m:
                base, aliq, valor = (parse_decimal_br(g) for g in m.groups())
                if None not in (base, aliq, valor):
                    tributos.append(
                        TributoExtraido(
                            tipo_tributo=tipo, base_calculo=base, aliquota=aliq, valor=valor
                        )
                    )
        return tributos

    def _medidas(self, t: str) -> list[MedidaExtraida]:
        m = _MEDIDOR.search(t)
        if not m:
            return []
        linha = m.group(0)
        serial = m.group(1)
        posto = self._posto(m.group(2))

        # As leituras/consumo podem estar na própria linha (pdfplumber) ou nas
        # linhas seguintes (pdftotext). O consumo é o último decimal da linha do
        # medidor; ant/atual/constante são os três primeiros decimais restantes.
        numeros_linha = re.findall(_DEC, linha)
        consumo = parse_decimal_br(numeros_linha[-1]) if numeros_linha else None
        restantes = numeros_linha[:-1]
        if len(restantes) < 3:
            for seguinte in t[m.end():].splitlines():
                restantes += re.findall(_DEC, seguinte)
                if len(restantes) >= 3:
                    break

        ant = parse_decimal_br(restantes[0]) if len(restantes) > 0 else Decimal("0")
        atual = parse_decimal_br(restantes[1]) if len(restantes) > 1 else Decimal("0")
        const = parse_decimal_br(restantes[2]) if len(restantes) > 2 else Decimal("1")
        return [
            MedidaExtraida(
                serial_medidor=serial,
                posto_horario=posto,
                leitura_anterior=ant or Decimal("0"),
                leitura_atual=atual or Decimal("0"),
                constante_medidor=const or Decimal("1"),
                consumo_kwh=consumo or Decimal("0"),
            )
        ]

    @staticmethod
    def _posto(texto: str) -> PostoHorario:
        t = texto.lower()
        if t.startswith("ponta"):
            return PostoHorario.PONTA
        if t.startswith("fora"):
            return PostoHorario.FORA_PONTA
        if t.startswith("intermedi"):
            return PostoHorario.INTERMEDIARIO
        return PostoHorario.UNICO

    @staticmethod
    def _confianca(fatura: FaturaExtraida) -> float:
        score = 1.0
        if fatura.valor_total <= 0:
            score -= 0.3
        if not fatura.medidas or fatura.medidas[0].consumo_kwh <= 0:
            score -= 0.25
        if not fatura.itens:
            score -= 0.25
        if fatura.chave_acesso is None:
            score -= 0.1
        if fatura.itens and fatura.valor_total > 0:
            soma = sum((i.valor for i in fatura.itens), Decimal("0"))
            if abs(soma - fatura.valor_total) > TOLERANCIA:
                # Itens não reconciliam com o total (bandeira/COSIP fora da tabela):
                # rebaixa para acionar o refino por IA quando disponível.
                score -= 0.2
        return round(max(score, 0.0), 2)
