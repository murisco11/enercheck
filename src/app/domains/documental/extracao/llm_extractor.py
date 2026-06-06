"""Fallback de extração via IA (OpenAI Structured Outputs).

Acionado apenas quando nenhum extrator determinístico atinge a confiança mínima.
A IA organiza o texto em campos; ela não calcula valor recuperável — isso permanece
com o motor determinístico.
"""

import logging

from src.app.core.ai import AIProvider
from src.app.domains.documental.extracao.schema import FaturaExtraida, ResultadoExtracao
from src.app.domains.documental.extracao.texto import DocumentoTexto

logger = logging.getLogger(__name__)

_INSTRUCOES = (
    "Você extrai dados de faturas de energia elétrica brasileiras. Receberá o texto "
    "de um documento que pode conter VÁRIAS faturas (competências diferentes). "
    "Para cada fatura, preencha os campos do schema. Use ponto como separador decimal "
    "(ex.: 1234.56). Competência no formato AAAA-MM e datas em AAAA-MM-DD. Não invente "
    "valores: se um campo não existir no texto, use null ou listas vazias."
)

_NUM = {"type": ["string", "null"]}
_STR = {"type": ["string", "null"]}

_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["faturas"],
    "properties": {
        "faturas": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "competencia", "numero_nota", "chave_acesso", "data_emissao",
                    "data_vencimento", "data_leitura_anterior", "data_leitura_atual",
                    "dias_faturados", "modalidade", "bandeira", "subgrupo",
                    "valor_total", "itens", "tributos", "medidas",
                ],
                "properties": {
                    "competencia": {"type": "string"},
                    "numero_nota": _STR,
                    "chave_acesso": _STR,
                    "data_emissao": _STR,
                    "data_vencimento": _STR,
                    "data_leitura_anterior": _STR,
                    "data_leitura_atual": _STR,
                    "dias_faturados": {"type": ["integer", "null"]},
                    "modalidade": _STR,
                    "bandeira": _STR,
                    "subgrupo": _STR,
                    "valor_total": {"type": "string"},
                    "itens": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["tipo_item", "descricao", "quantidade",
                                         "tarifa_unitaria", "valor"],
                            "properties": {
                                "tipo_item": {"type": "string"},
                                "descricao": {"type": "string"},
                                "quantidade": {"type": "string"},
                                "tarifa_unitaria": {"type": "string"},
                                "valor": {"type": "string"},
                            },
                        },
                    },
                    "tributos": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["tipo_tributo", "base_calculo", "aliquota", "valor"],
                            "properties": {
                                "tipo_tributo": {"type": "string"},
                                "base_calculo": {"type": "string"},
                                "aliquota": {"type": "string"},
                                "valor": {"type": "string"},
                            },
                        },
                    },
                    "medidas": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["serial_medidor", "posto_horario",
                                         "leitura_anterior", "leitura_atual",
                                         "constante_medidor", "consumo_kwh"],
                            "properties": {
                                "serial_medidor": _STR,
                                "posto_horario": {"type": "string"},
                                "leitura_anterior": _NUM,
                                "leitura_atual": _NUM,
                                "constante_medidor": _NUM,
                                "consumo_kwh": _NUM,
                            },
                        },
                    },
                },
            },
        }
    },
}


def extrair_via_ia(doc: DocumentoTexto, provider: AIProvider) -> ResultadoExtracao:
    bruto = provider.extrair_estruturado(doc.layout, _SCHEMA, _INSTRUCOES)
    faturas: list[FaturaExtraida] = []
    for item in bruto.get("faturas", []):
        item = {k: v for k, v in item.items() if v is not None or k == "valor_total"}
        item.setdefault("valor_total", "0")
        faturas.append(FaturaExtraida(**item, confianca=0.7))
    return ResultadoExtracao(
        faturas=faturas,
        metodo=f"ia:{provider.nome}",
        confianca=0.7 if faturas else 0.0,
    )
