"""Dropdowns dinâmicos no Swagger para campos de ID.

Em vez de digitar UUIDs à mão, o /docs passa a oferecer um *select* com as opções
existentes no banco. Isso é feito reescrevendo o schema OpenAPI a cada carga (não
cacheado), injetando ``enum`` (os IDs) e uma legenda id→rótulo na descrição dos
campos que referenciam outras entidades.

É um recurso de conveniência para desenvolvimento; se o banco estiver indisponível,
o schema base é servido sem os selects.
"""

import logging

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from sqlalchemy import select

logger = logging.getLogger(__name__)

# Nome do campo/parametro -> chave de entidade (usado em corpos JSON e forms).
NOME_PARA_ENTIDADE = {
    "distribuidora_id": "distribuidora",
    "cliente_id": "cliente",
    "unidade_consumidora_id": "uc",
    "lote_auditoria_id": "lote",
    "usuario_id": "usuario",
    "responsavel_id": "usuario",
    "fatura_id": "fatura",
    "achado_id": "achado",
    "documento_bruto_id": "documento",
}

# Parâmetros de rota ({id}, {uc_id}...) por prefixo de caminho (mais específico 1º).
ROTA_PARA_ENTIDADE: list[tuple[str, dict[str, str]]] = [
    ("/v1/clientes/{id}/ucs/{uc_id}", {"id": "cliente", "uc_id": "uc"}),
    ("/v1/clientes/{id}/acessos", {"id": "cliente"}),
    ("/v1/clientes/{id}/ucs", {"id": "cliente"}),
    ("/v1/clientes/{id}", {"id": "cliente"}),
    ("/v1/distribuidoras/{id}", {"id": "distribuidora"}),
    ("/v1/faturas/{id}", {"id": "fatura"}),
    ("/v1/lotes/{id}", {"id": "lote"}),
    ("/v1/achados/{id}", {"id": "achado"}),
    ("/v1/documental/documentos/{id}", {"id": "documento"}),
]

_LIMITE = 200


def _carregar_opcoes() -> dict[str, list[tuple[str, str]]]:
    """Carrega, por entidade, uma lista de (id, rótulo) a partir do banco."""
    from src.app.api.v1.dependencies import get_session_manager
    from src.app.domains.auditoria.models import Achado
    from src.app.domains.auth.models import Usuario
    from src.app.domains.clientes.models import (
        Cliente,
        Distribuidora,
        LoteAuditoria,
        UnidadeConsumidora,
    )
    from src.app.domains.documental.models import DocumentoBruto
    from src.app.domains.faturas.models import Fatura

    manager = get_session_manager()
    with manager.session_factory() as db:
        def opcoes(stmt, rotulo):
            return [(str(obj.id), rotulo(obj)) for obj in db.scalars(stmt.limit(_LIMITE)).all()]

        return {
            "distribuidora": opcoes(
                select(Distribuidora), lambda o: f"{o.sigla} — {o.razao_social}"
            ),
            "cliente": opcoes(select(Cliente), lambda o: f"{o.razao_social} ({o.cnpj})"),
            "uc": opcoes(
                select(UnidadeConsumidora),
                lambda o: f"{o.codigo_instalacao} — {o.cidade}/{o.estado}",
            ),
            "lote": opcoes(select(LoteAuditoria), lambda o: o.rotulo),
            "usuario": opcoes(select(Usuario), lambda o: f"{o.nome} <{o.email}>"),
            "fatura": opcoes(
                select(Fatura), lambda o: f"{o.competencia} — R$ {o.valor_total}"
            ),
            "achado": opcoes(select(Achado), lambda o: o.titulo),
            "documento": opcoes(select(DocumentoBruto), lambda o: o.nome_original),
        }


def _aplicar_enum(schema: dict, opcoes: list[tuple[str, str]]) -> None:
    if not opcoes:
        return
    ids = [id_ for id_, _ in opcoes]
    legenda = "\n".join(f"- `{id_}`: {rotulo}" for id_, rotulo in opcoes)

    # Campo opcional vem como anyOf [string, null]; o enum vai no ramo string.
    ramos = schema.get("anyOf") or schema.get("oneOf")
    if ramos:
        for ramo in ramos:
            if ramo.get("type") == "string":
                ramo["enum"] = ids
    else:
        schema["enum"] = ids
    schema["description"] = f"Selecione uma opção existente:\n{legenda}"


def _injetar(openapi_schema: dict, opcoes: dict[str, list[tuple[str, str]]]) -> None:
    # 1) Propriedades de corpos JSON e formulários (multipart) por nome de campo.
    for schema in openapi_schema.get("components", {}).get("schemas", {}).values():
        for nome, prop in schema.get("properties", {}).items():
            entidade = NOME_PARA_ENTIDADE.get(nome)
            if entidade:
                _aplicar_enum(prop, opcoes.get(entidade, []))

    # 2) Parâmetros de rota/query por caminho e nome.
    for caminho, operacoes in openapi_schema.get("paths", {}).items():
        mapa_rota = _mapa_para_caminho(caminho)
        for operacao in operacoes.values():
            if not isinstance(operacao, dict):
                continue
            for parametro in operacao.get("parameters", []):
                nome = parametro.get("name")
                entidade = NOME_PARA_ENTIDADE.get(nome) or mapa_rota.get(nome)
                if entidade and "schema" in parametro:
                    _aplicar_enum(parametro["schema"], opcoes.get(entidade, []))


def _mapa_para_caminho(caminho: str) -> dict[str, str]:
    for prefixo, mapa in ROTA_PARA_ENTIDADE:
        if caminho == prefixo or caminho.startswith(prefixo + "/"):
            return mapa
    return {}


def configurar_selects_openapi(app: FastAPI) -> None:
    def openapi_custom():
        schema = get_openapi(
            title=app.title,
            version=app.version,
            routes=app.routes,
            description=app.description or None,
        )
        try:
            _injetar(schema, _carregar_opcoes())
        except Exception as exc:  # noqa: BLE001 - docs nunca devem quebrar por causa disso
            logger.warning("Não foi possível popular os selects do Swagger: %s", exc)
        # Não cacheia: reflete o estado atual do banco a cada carga do /docs.
        app.openapi_schema = None
        return schema

    app.openapi = openapi_custom
