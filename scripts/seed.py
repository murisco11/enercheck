"""Seed da base regulatória mínima para a Neoenergia Cosern (RN).

Popula distribuidora, layouts de fatura (para detecção/extração), um pacote de
regras vigente com regras DSL e snapshots tarifários cobrindo as competências das
faturas de exemplo. As tarifas refletem os valores impressos nas próprias faturas,
de modo que uma fatura correta passa na validação — o sistema só aponta achado
quando há divergência real.

Uso::

    uv run python -m scripts.seed
"""

import logging
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.app.api.v1.dependencies import get_session_manager
from src.app.core.enums import Grupo, ModalidadeTarifaria, PapelUsuario, StatusLote, Subgrupo
from src.app.domains.auth.models import Usuario
from src.app.domains.auth.repository import UsuarioRepository
from src.app.domains.clientes.models import (
    Cliente,
    Distribuidora,
    LoteAuditoria,
    UnidadeConsumidora,
)
from src.app.domains.documental.models import LayoutFatura
from src.app.domains.regulatorio.enums import CategoriaRegra, Severidade
from src.app.domains.regulatorio.models import PacoteRegras, RegraValidacao, SnapshotTarifa

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed")

COSERN_CNPJ = "08324196000181"
ADMIN_EMAIL = "admin@enercheck.local"
ADMIN_SENHA = "Admin1234"
CLIENTE_DEMO_CNPJ = "12345678000199"


def seed(db: Session) -> None:
    distribuidora = _distribuidora(db)
    _layouts(db, distribuidora.id)
    pacote = _pacote_regras(db)
    _regras(db, pacote.id)
    _snapshots(db, distribuidora.id)

    admin = _admin_demo(db)
    cliente = _cliente_demo(db)
    uc = _uc_demo(db, cliente.id, distribuidora.id)
    lote = _lote_demo(db, uc.id, admin.id)
    db.commit()

    logger.info("Seed concluído.")
    logger.info("--- Dados de demonstração ---")
    logger.info("Admin:        %s / senha: %s", ADMIN_EMAIL, ADMIN_SENHA)
    logger.info("Distribuidora: %s (%s)", distribuidora.sigla, distribuidora.id)
    logger.info("Cliente:       %s (%s)", cliente.razao_social, cliente.id)
    logger.info("UC:            %s (%s)", uc.codigo_instalacao, uc.id)
    logger.info("Lote:          %s (%s)", lote.rotulo, lote.id)


def _distribuidora(db: Session) -> Distribuidora:
    dist = db.scalar(select(Distribuidora).where(Distribuidora.cnpj == COSERN_CNPJ))
    if dist is None:
        dist = Distribuidora(
            razao_social="Companhia Energética do Rio Grande do Norte",
            cnpj=COSERN_CNPJ,
            sigla="COSERN",
            estado="RN",
        )
        db.add(dist)
        db.flush()
        logger.info("Distribuidora Cosern criada.")
    return dist


def _layouts(db: Session, distribuidora_id) -> None:  # noqa: ANN001
    definicoes = [
        {
            "codigo": "cosern_2022",
            "descricao": "Cosern - layout 2022 (DESCRIÇÃO DA NOTA FISCAL)",
            "extrator_classe": "cosern_2022",
            "vigencia_inicio": date(2015, 1, 1),
            "vigencia_fim": date(2024, 12, 31),
            "assinatura_deteccao": {
                "all": ["DESCRIÇÃO DA NOTA FISCAL", "DEMONSTRATIVO DE CONSUMO"]
            },
        },
        {
            "codigo": "cosern_nf3e",
            "descricao": "Cosern - layout NF3e (DANFE)",
            "extrator_classe": "cosern_nf3e",
            "vigencia_inicio": date(2024, 1, 1),
            "vigencia_fim": None,
            "assinatura_deteccao": {
                "all": ["ITENS DA FATURA"],
                "any": ["chave de acesso", "DANFE"],
            },
        },
    ]
    for definicao in definicoes:
        existe = db.scalar(select(LayoutFatura).where(LayoutFatura.codigo == definicao["codigo"]))
        if existe is None:
            db.add(LayoutFatura(distribuidora_id=distribuidora_id, ativo=True, **definicao))
            logger.info("Layout %s criado.", definicao["codigo"])


def _pacote_regras(db: Session) -> PacoteRegras:
    pacote = db.scalar(select(PacoteRegras).where(PacoteRegras.versao == "cosern-v1"))
    if pacote is None:
        pacote = PacoteRegras(
            versao="cosern-v1",
            descricao="Pacote inicial de regras Cosern (B1 convencional).",
            vigente=True,
            ativo=True,
        )
        db.add(pacote)
        db.flush()
        logger.info("Pacote de regras cosern-v1 criado e marcado como vigente.")
    return pacote


def _regras(db: Session, pacote_id) -> None:  # noqa: ANN001
    definicoes = [
        {
            "codigo": "COSERN-CONSUMO",
            "nome": "Consumo confere com as leituras",
            "categoria": CategoriaRegra.MEDICAO,
            "severidade": Severidade.ALTA,
            "expressao_logica": {"tipo": "recalculo_consumo", "tolerancia": "0.01"},
        },
        {
            "codigo": "COSERN-TUSD",
            "nome": "Valor da TUSD confere com a tarifa vigente",
            "categoria": CategoriaRegra.TARIFA,
            "severidade": Severidade.ALTA,
            "expressao_logica": {
                "tipo": "valor_item_por_tarifa",
                "tipo_item": "tusd",
                "campo_snapshot": "valor_tusd_com_tributos",
                "tolerancia": "0.50",
            },
        },
        {
            "codigo": "COSERN-TE",
            "nome": "Valor da TE confere com a tarifa vigente",
            "categoria": CategoriaRegra.TARIFA,
            "severidade": Severidade.ALTA,
            "expressao_logica": {
                "tipo": "valor_item_por_tarifa",
                "tipo_item": "te",
                "campo_snapshot": "valor_te_com_tributos",
                "tolerancia": "0.50",
            },
        },
    ]
    for definicao in definicoes:
        existe = db.scalar(
            select(RegraValidacao).where(RegraValidacao.codigo == definicao["codigo"])
        )
        if existe is None:
            db.add(
                RegraValidacao(
                    pacote_regras_id=pacote_id,
                    aplica_grupo=Grupo.B,
                    aplica_subgrupo=Subgrupo.B1,
                    aplica_modalidade=ModalidadeTarifaria.CONVENCIONAL,
                    ativa=True,
                    **definicao,
                )
            )
            logger.info("Regra %s criada.", definicao["codigo"])


def _snapshots(db: Session, distribuidora_id) -> None:  # noqa: ANN001
    base = {
        "distribuidora_id": distribuidora_id,
        "grupo": Grupo.B,
        "subgrupo": Subgrupo.B1,
        "modalidade": ModalidadeTarifaria.CONVENCIONAL,
    }
    snapshots = [
        {
            **base,
            "vigencia_inicio": date(2021, 1, 1),
            "vigencia_fim": date(2024, 12, 31),
            "valor_tusd": Decimal("0.31340"),
            "valor_te": Decimal("0.24564"),
            "valor_tusd_com_tributos": Decimal("0.40867741"),
            "valor_te_com_tributos": Decimal("0.32031755"),
            "resolucao_origem": "REH ANEEL 2021 (Cosern)",
        },
        {
            **base,
            "vigencia_inicio": date(2025, 1, 1),
            "vigencia_fim": None,
            "valor_tusd": Decimal("0.43260"),
            "valor_te": Decimal("0.31164"),
            "valor_tusd_com_tributos": Decimal("0.57422746"),
            "valor_te_com_tributos": Decimal("0.41366677"),
            "resolucao_origem": "REH ANEEL 2025 (Cosern)",
        },
    ]
    for snap in snapshots:
        existe = db.scalar(
            select(SnapshotTarifa)
            .where(SnapshotTarifa.distribuidora_id == distribuidora_id)
            .where(SnapshotTarifa.subgrupo == Subgrupo.B1)
            .where(SnapshotTarifa.modalidade == ModalidadeTarifaria.CONVENCIONAL)
            .where(SnapshotTarifa.vigencia_inicio == snap["vigencia_inicio"])
        )
        if existe is None:
            db.add(SnapshotTarifa(**snap))
            logger.info("Snapshot tarifário %s criado.", snap["vigencia_inicio"])


def _admin_demo(db: Session) -> Usuario:
    admin = db.scalar(select(Usuario).where(Usuario.email == ADMIN_EMAIL))
    if admin is None:
        admin = Usuario(
            nome="Admin Demo",
            email=ADMIN_EMAIL,
            senha_hash=UsuarioRepository._hash_senha(ADMIN_SENHA),
            papel=PapelUsuario.ADMIN,
            ativo=True,
        )
        db.add(admin)
        db.flush()
        logger.info("Usuário admin de demonstração criado.")
    return admin


def _cliente_demo(db: Session) -> Cliente:
    cliente = db.scalar(select(Cliente).where(Cliente.cnpj == CLIENTE_DEMO_CNPJ))
    if cliente is None:
        cliente = Cliente(
            razao_social="Cliente Demonstração LTDA",
            nome_fantasia="Cliente Demo",
            cnpj=CLIENTE_DEMO_CNPJ,
        )
        db.add(cliente)
        db.flush()
        logger.info("Cliente de demonstração criado.")
    return cliente


def _uc_demo(db: Session, cliente_id, distribuidora_id) -> UnidadeConsumidora:  # noqa: ANN001
    uc = db.scalar(
        select(UnidadeConsumidora)
        .where(UnidadeConsumidora.distribuidora_id == distribuidora_id)
        .where(UnidadeConsumidora.codigo_instalacao == "DEMO-001")
    )
    if uc is None:
        uc = UnidadeConsumidora(
            cliente_id=cliente_id,
            distribuidora_id=distribuidora_id,
            codigo_instalacao="DEMO-001",
            grupo=Grupo.B,
            subgrupo=Subgrupo.B1,
            modalidade=ModalidadeTarifaria.CONVENCIONAL,
            cidade="Natal",
            estado="RN",
        )
        db.add(uc)
        db.flush()
        logger.info("Unidade consumidora de demonstração criada.")
    return uc


def _lote_demo(db: Session, uc_id, criado_por_id) -> LoteAuditoria:  # noqa: ANN001
    lote = db.scalar(
        select(LoteAuditoria)
        .where(LoteAuditoria.unidade_consumidora_id == uc_id)
        .where(LoteAuditoria.rotulo == "Lote de demonstração")
    )
    if lote is None:
        lote = LoteAuditoria(
            unidade_consumidora_id=uc_id,
            criado_por_id=criado_por_id,
            rotulo="Lote de demonstração",
            status=StatusLote.PENDENTE,
            competencia_inicio=date(2021, 1, 1),
            competencia_fim=date(2025, 12, 31),
        )
        db.add(lote)
        db.flush()
        logger.info("Lote de demonstração criado.")
    return lote


def main() -> None:
    manager = get_session_manager()
    manager.create_tables()
    with manager.session_factory() as db:
        seed(db)


if __name__ == "__main__":
    main()
