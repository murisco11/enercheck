from enum import StrEnum


class Severidade(StrEnum):
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"


class OrigemRegulatoria(StrEnum):
    ANEEL = "aneel"
    DISTRIBUIDORA = "distribuidora"
    INMETRO = "inmetro"
    OUTRO = "outro"


class TipoDocumento(StrEnum):
    RESOLUCAO_NORMATIVA = "resolucao_normativa"
    RESOLUCAO_HOMOLOGATORIA = "resolucao_homologatoria"
    NOTA_TECNICA = "nota_tecnica"
    PORTARIA = "portaria"
    DESPACHO = "despacho"
    OUTRO = "outro"


class StatusDocumento(StrEnum):
    ATIVO = "ativo"
    REVOGADO = "revogado"
    SUBSTITUIDO = "substituido"

class CategoriaRegra(StrEnum):
    COBRANCA_INDEVIDA = "cobranca_indevida"
    MEDICAO = "medicao"
    DEMANDA = "demanda"
    TRIBUTOS = "tributos"
    TARIFA = "tarifa"
    BANDEIRA = "bandeira"
    DUPLICIDADE = "duplicidade"
    OUTRO = "outro"
