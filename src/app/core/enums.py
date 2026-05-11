from enum import StrEnum


class PapelUsuario(StrEnum):
    ADMIN = "admin"
    CONSULTOR = "consultor"
    VISUALIZADOR = "visualizador"


class Bandeira(StrEnum):
    VERDE = "verde"
    AMARELA = "amarela"
    VERMELHA_1 = "vermelha_1"
    VERMELHA_2 = "vermelha_2"
    ESCASSEZ = "escassez"


class ModalidadeTarifaria(StrEnum):
    AZUL = "azul"
    VERDE = "verde"
    CONVENCIONAL = "convencional"
    BRANCA = "branca"


class Grupo(StrEnum):
    A = "A"
    B = "B"


class Subgrupo(StrEnum):
    A1 = "A1"
    A2 = "A2"
    A3 = "A3"
    A3a = "A3a"
    A4 = "A4"
    AS = "AS"
    B1 = "B1"
    B2 = "B2"
    B3 = "B3"
    B4 = "B4"


class StatusLote(StrEnum):
    PENDENTE = "pendente"
    PROCESSANDO = "processando"
    CONCLUIDO = "concluido"
    ERRO = "erro"


class StatusExtracao(StrEnum):
    PENDENTE = "pendente"
    PROCESSANDO = "processando"
    CONCLUIDO = "concluido"
    ERRO = "erro"


class StatusAchado(StrEnum):
    ABERTO = "aberto"
    CONFIRMADO = "confirmado"
    DESCARTADO = "descartado"
    RECUPERADO = "recuperado"


class StatusRecuperacao(StrEnum):
    ABERTO = "aberto"
    EM_NEGOCIACAO = "em_negociacao"
    CONCLUIDO = "concluido"
    CANCELADO = "cancelado"


class SeveridadeRegra(StrEnum):
    CRITICA = "critica"
    ALTA = "alta"
    MEDIA = "media"
    BAIXA = "baixa"


class CanalRecuperacao(StrEnum):
    PORTAL = "portal"
    EMAIL = "email"
    PRESENCIAL = "presencial"
    JUDICIAL = "judicial"


class ModoDevolucao(StrEnum):
    CREDITO_FATURA = "credito_fatura"
    DEPOSITO = "deposito"
    COMPENSACAO = "compensacao"


class PostoHorario(StrEnum):
    PONTA = "ponta"
    FORA_PONTA = "fora_ponta"
    INTERMEDIARIO = "intermediario"
    UNICO = "unico"
