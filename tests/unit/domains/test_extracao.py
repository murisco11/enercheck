"""Testes da extração: helpers de parsing, extrator Cosern 2022 (texto sintético) e,
opcionalmente, os PDFs reais (pulados quando ausentes, para não versionar dados
pessoais)."""

import os
from decimal import Decimal
from pathlib import Path

import pytest

from src.app.core.enums import Bandeira, ModalidadeTarifaria, Subgrupo, TipoItem
from src.app.domains.documental.extracao.base import (
    competencia_mm_aaaa,
    mapear_tipo_item,
    normalizar_chave,
    parse_data_br,
    parse_decimal_br,
)
from src.app.domains.documental.extracao.extratores.cosern_2022 import CosernExtrator2022
from src.app.domains.documental.extracao.extratores.cosern_nf3e import CosernExtratorNF3e
from src.app.domains.documental.extracao.texto import DocumentoTexto, extrair_documento_texto

# Fluxo (pdfplumber em ordem de leitura) sintético e anonimizado do layout 2022.
FLUXO_2022 = """DADOS DO CLIENTE DATA DE VENCIMENTO DATA DA EMISSÃO DA NOTA FISCAL CONTA CONTRATO
FULANO DE TAL 05/01/2022 08/12/2021 7015589552
TOTAL A PAGAR (R$) NÚMERO DA NOTA FISCAL
0,00 071068915 Nº DA INSTALAÇÃO
CLASSIFICAÇÃO
ZONA RURAL B1 RESIDENCIAL - RESIDENCIAL
Conv. Monômia - Trifásico
DESCRIÇÃO DA NOTA FISCAL
QUANTIDADE PREÇO(R$) VALOR(R$)
Consumo Ativo(kWh)-TUSD 100,0000000 0,40867741 40,86
Consumo Ativo(kWh)-TE 100,0000000 0,32031755 32,03
Acréscimo Bandeira AMARELA 18,51
Contrib. Ilum. Pública Municipal 5,00
Multa por atraso 1,78
Juros por atraso 0,35
Atualizacao IPCA 0,31
Tarifas Aplicadas
TOTAL DA FATURA 98,84
INFORMAÇÕES DE TRIBUTOS
91,40 18,00 16,45 74,94 1,16 0,86 74,94 5,32 3,98
DEMONSTRATIVO DE CONSUMO DESTA NOTA FISCAL
2171132692 CAT 05/11/2021 2.808,00 06/12/2021 2.885,00 31 1,00000 77,00-
DESTAQUE AQUI
CONTA CONTRATO MÊS/ANO
7015589552 12/2021 0,00 05/01/2022
"""


def _pdf_sample(nome: str) -> Path | None:
    base = Path(os.environ.get("SAMPLE_PDF_DIR", str(Path.home() / "Downloads")))
    caminho = base / nome
    return caminho if caminho.exists() else None


class TestHelpersParsing:
    def test_decimal_br_milhar_e_sinal(self):
        assert parse_decimal_br("1.234,56") == Decimal("1234.56")
        assert parse_decimal_br("77,00-") == Decimal("-77.00")
        assert parse_decimal_br("") is None

    def test_data_e_competencia(self):
        assert parse_data_br("05/01/2022") == "2022-01-05"
        assert competencia_mm_aaaa("12/2021") == "2021-12"

    def test_normalizar_chave(self):
        chave = "2425 1108 3241 9600 0181 6600 0148 8171 8010 5421 6100"
        assert normalizar_chave(chave) == "24251108324196000181660001488171801054216100"
        assert normalizar_chave("123") is None

    def test_mapear_tipo_item(self):
        assert mapear_tipo_item("Consumo Ativo(kWh)-TUSD") == TipoItem.TUSD
        assert mapear_tipo_item("Consumo-TE") == TipoItem.TE
        assert mapear_tipo_item("Contrib. Ilum. Pública Municipal") == TipoItem.COSIP
        assert mapear_tipo_item("Multa por atraso") == TipoItem.MULTA


class TestExtrator2022Sintetico:
    def test_extrai_fatura_completa(self):
        doc = DocumentoTexto(layout="", fluxo=FLUXO_2022)
        resultado = CosernExtrator2022().extrair(doc)
        assert len(resultado.faturas) == 1
        f = resultado.faturas[0]
        assert f.competencia == "2021-12"
        assert f.data_vencimento == "2022-01-05"
        assert f.data_emissao == "2021-12-08"
        assert f.numero_nota == "071068915"
        assert f.subgrupo == Subgrupo.B1
        assert f.modalidade == ModalidadeTarifaria.CONVENCIONAL
        assert f.bandeira == Bandeira.AMARELA
        assert f.valor_total == Decimal("98.84")
        assert sum(i.valor for i in f.itens) == Decimal("98.84")
        assert resultado.confianca == 1.0

    def test_medida_e_tributos(self):
        f = CosernExtrator2022().extrair(DocumentoTexto(layout="", fluxo=FLUXO_2022)).faturas[0]
        assert len(f.medidas) == 1
        assert f.medidas[0].consumo_kwh == Decimal("77.00")
        assert {t.tipo_tributo.value for t in f.tributos} == {"icms", "pis", "cofins"}


class TestPdfsReais:
    def test_cosern_2022_real(self):
        pdf = _pdf_sample("COSERN - 01.22.pdf")
        if pdf is None:
            pytest.skip("PDF de exemplo 2022 ausente.")
        doc = extrair_documento_texto(pdf.read_bytes())
        f = CosernExtrator2022().extrair(doc).faturas[0]
        assert f.competencia == "2021-12"
        assert f.valor_total == Decimal("98.84")
        assert f.medidas[0].consumo_kwh == Decimal("77.00")

    def test_cosern_nf3e_real_multifatura(self):
        pdf = _pdf_sample("000856926451.pdf")
        if pdf is None:
            pytest.skip("PDF de exemplo NF3e ausente.")
        doc = extrair_documento_texto(pdf.read_bytes())
        resultado = CosernExtratorNF3e().extrair(doc)
        assert len(resultado.faturas) == 10
        assert len({f.chave_acesso for f in resultado.faturas}) == 10
        primeira = resultado.faturas[0]
        assert primeira.competencia == "2025-11"
        assert len(primeira.chave_acesso) == 44
        assert primeira.medidas[0].consumo_kwh == Decimal("898.00")
