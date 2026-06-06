import uuid
from datetime import date

from sqlalchemy import desc, or_, select
from sqlalchemy.orm import Session

from src.app.core.enums import Grupo, ModalidadeTarifaria, PostoHorario, Subgrupo
from src.app.domains.regulatorio.models import (
    ChunkRegulatorio,
    DocumentoRegulatorio,
    PacoteRegras,
    RegraValidacao,
    SnapshotTarifa,
)
from src.app.domains.regulatorio.schemas import (
    DocumentoRegulatorioUpdate,
    PacoteRegrasUpdate,
    RegraValidacaoUpdate,
    SnapshotTarifaUpdate,
)


class DocumentoRegulatorioRepository:
    def __init__(self, session: Session):
        self._s = session

    def criar(self, doc: DocumentoRegulatorio) -> DocumentoRegulatorio:
        self._s.add(doc)
        self._s.flush()
        return doc

    def buscar_por_id(self, doc_id: uuid.UUID) -> DocumentoRegulatorio | None:
        return self._s.get(DocumentoRegulatorio, doc_id)

    def listar(self) -> list[DocumentoRegulatorio]:
        return list(
            self._s.execute(select(DocumentoRegulatorio).order_by(DocumentoRegulatorio.titulo))
            .scalars()
            .all()
        )

    def atualizar(self, doc: DocumentoRegulatorio, dados: DocumentoRegulatorioUpdate) -> None:
        for campo, valor in dados.model_dump(exclude_unset=True).items():
            setattr(doc, campo, valor)
        self._s.flush()

    def desativar(self, doc: DocumentoRegulatorio) -> None:
        doc.ativo = False
        self._s.flush()

    def remover(self, doc: DocumentoRegulatorio) -> None:
        self._s.delete(doc)
        self._s.flush()


class ChunkRegulatorioRepository:
    def __init__(self, session: Session):
        self._s = session

    def criar_lote(self, chunks: list[ChunkRegulatorio]) -> None:
        self._s.add_all(chunks)
        self._s.flush()

    def listar_por_documento(self, documento_id: uuid.UUID) -> list[ChunkRegulatorio]:
        return list(
            self._s.execute(
                select(ChunkRegulatorio)
                .where(ChunkRegulatorio.documento_regulatorio_id == documento_id)
                .order_by(ChunkRegulatorio.indice)
            )
            .scalars()
            .all()
        )


class SnapshotTarifaRepository:
    def __init__(self, session: Session):
        self._s = session

    def criar(self, snap: SnapshotTarifa) -> SnapshotTarifa:
        self._s.add(snap)
        self._s.flush()
        return snap

    def listar(self, distribuidora_id: uuid.UUID | None = None) -> list[SnapshotTarifa]:
        stmt = select(SnapshotTarifa).order_by(
            SnapshotTarifa.distribuidora_id,
            desc(SnapshotTarifa.vigencia_inicio),
        )
        if distribuidora_id is not None:
            stmt = stmt.where(SnapshotTarifa.distribuidora_id == distribuidora_id)
        return list(self._s.execute(stmt).scalars().all())

    def buscar_por_id(self, snap_id: uuid.UUID) -> SnapshotTarifa | None:
        return self._s.get(SnapshotTarifa, snap_id)

    def resolver(
        self,
        *,
        distribuidora_id: uuid.UUID,
        grupo: Grupo,
        subgrupo: Subgrupo,
        modalidade: ModalidadeTarifaria,
        competencia: date,
        posto: PostoHorario | None = None,
    ) -> SnapshotTarifa | None:
        """Snapshot tarifário vigente na competência para a configuração da UC.

        O posto é casado quando informado, mas snapshots sem posto (genéricos)
        também são aceitos. Em caso de empate, vence a vigência mais recente.
        """
        stmt = (
            select(SnapshotTarifa)
            .where(SnapshotTarifa.ativo.is_(True))
            .where(SnapshotTarifa.distribuidora_id == distribuidora_id)
            .where(SnapshotTarifa.grupo == grupo)
            .where(SnapshotTarifa.subgrupo == subgrupo)
            .where(SnapshotTarifa.modalidade == modalidade)
            .where(SnapshotTarifa.vigencia_inicio <= competencia)
            .where(
                or_(
                    SnapshotTarifa.vigencia_fim.is_(None),
                    SnapshotTarifa.vigencia_fim >= competencia,
                )
            )
            .order_by(desc(SnapshotTarifa.vigencia_inicio))
        )
        if posto is not None:
            stmt = stmt.where(
                or_(
                    SnapshotTarifa.posto_horario == posto,
                    SnapshotTarifa.posto_horario.is_(None),
                )
            )
        return self._s.execute(stmt).scalars().first()

    def atualizar(self, snap: SnapshotTarifa, dados: SnapshotTarifaUpdate) -> None:
        for campo, valor in dados.model_dump(exclude_unset=True).items():
            setattr(snap, campo, valor)
        self._s.flush()

    def desativar(self, snap: SnapshotTarifa) -> None:
        snap.ativo = False
        self._s.flush()

    def remover(self, snap: SnapshotTarifa) -> None:
        self._s.delete(snap)
        self._s.flush()

    def existe_sobreposicao(
        self, snap: SnapshotTarifa, ignorar_id: uuid.UUID | None = None
    ) -> bool:
        fim = snap.vigencia_fim or date.max
        stmt = (
            select(SnapshotTarifa.id)
            .where(SnapshotTarifa.ativo.is_(True))
            .where(SnapshotTarifa.distribuidora_id == snap.distribuidora_id)
            .where(SnapshotTarifa.grupo == snap.grupo)
            .where(SnapshotTarifa.subgrupo == snap.subgrupo)
            .where(SnapshotTarifa.modalidade == snap.modalidade)
            .where(self._nullable_equals(SnapshotTarifa.posto_horario, snap.posto_horario))
            .where(self._nullable_equals(SnapshotTarifa.bandeira, snap.bandeira))
            .where(SnapshotTarifa.vigencia_inicio <= fim)
            .where(
                or_(
                    SnapshotTarifa.vigencia_fim.is_(None),
                    SnapshotTarifa.vigencia_fim >= snap.vigencia_inicio,
                )
            )
            .limit(1)
        )
        if ignorar_id is not None:
            stmt = stmt.where(SnapshotTarifa.id != ignorar_id)
        return self._s.execute(stmt).scalar_one_or_none() is not None

    @staticmethod
    def _nullable_equals(column, value):
        if value is None:
            return column.is_(None)
        return column == value


class PacoteRegrasRepository:
    def __init__(self, session: Session):
        self._s = session

    def criar(self, pacote: PacoteRegras) -> PacoteRegras:
        self._s.add(pacote)
        self._s.flush()
        return pacote

    def listar(self) -> list[PacoteRegras]:
        return list(
            self._s.execute(select(PacoteRegras).order_by(desc(PacoteRegras.criado_em)))
            .scalars()
            .all()
        )

    def buscar_por_id(self, pacote_id: uuid.UUID) -> PacoteRegras | None:
        return self._s.get(PacoteRegras, pacote_id)

    def buscar_vigente(self) -> PacoteRegras | None:
        stmt = (
            select(PacoteRegras)
            .where(PacoteRegras.vigente.is_(True))
            .where(PacoteRegras.ativo.is_(True))
            .order_by(desc(PacoteRegras.criado_em))
        )
        return self._s.execute(stmt).scalars().first()

    def atualizar(self, pacote: PacoteRegras, dados: PacoteRegrasUpdate) -> None:
        for campo, valor in dados.model_dump(exclude_unset=True).items():
            setattr(pacote, campo, valor)
        self._s.flush()

    def limpar_vigente(self, exceto_id: uuid.UUID | None = None) -> None:
        stmt = select(PacoteRegras).where(PacoteRegras.vigente.is_(True))
        if exceto_id is not None:
            stmt = stmt.where(PacoteRegras.id != exceto_id)
        for pacote in self._s.execute(stmt).scalars().all():
            pacote.vigente = False
        self._s.flush()

    def desativar(self, pacote: PacoteRegras) -> None:
        pacote.ativo = False
        self._s.flush()

    def remover(self, pacote: PacoteRegras) -> None:
        self._s.delete(pacote)
        self._s.flush()


class RegraValidacaoRepository:
    def __init__(self, session: Session):
        self._s = session

    def criar(self, regra: RegraValidacao) -> RegraValidacao:
        self._s.add(regra)
        self._s.flush()
        return regra

    def buscar_por_id(self, regra_id: uuid.UUID) -> RegraValidacao | None:
        return self._s.get(RegraValidacao, regra_id)

    def atualizar(self, regra: RegraValidacao, dados: RegraValidacaoUpdate) -> None:
        for campo, valor in dados.model_dump(exclude_unset=True).items():
            setattr(regra, campo, valor)
        self._s.flush()

    def desativar(self, regra: RegraValidacao) -> None:
        regra.ativa = False
        self._s.flush()

    def remover(self, regra: RegraValidacao) -> None:
        self._s.delete(regra)
        self._s.flush()

    def listar_por_pacote(
        self, pacote_id: uuid.UUID, apenas_ativas: bool = True
    ) -> list[RegraValidacao]:
        stmt = select(RegraValidacao).where(RegraValidacao.pacote_regras_id == pacote_id)
        if apenas_ativas:
            stmt = stmt.where(RegraValidacao.ativa.is_(True))
        return list(self._s.execute(stmt.order_by(RegraValidacao.codigo)).scalars().all())

    def listar_aplicaveis(
        self,
        pacote_id: uuid.UUID,
        *,
        grupo: Grupo,
        subgrupo: Subgrupo,
        modalidade: ModalidadeTarifaria,
        competencia: date,
    ) -> list[RegraValidacao]:
        """Regras ativas do pacote cujo escopo e vigência cobrem a fatura.

        Um campo de escopo nulo (aplica_grupo/subgrupo/modalidade) significa "vale
        para qualquer valor". A vigência nula significa "sempre vigente".
        """
        stmt = (
            select(RegraValidacao)
            .where(RegraValidacao.pacote_regras_id == pacote_id)
            .where(RegraValidacao.ativa.is_(True))
            .where(or_(RegraValidacao.aplica_grupo.is_(None), RegraValidacao.aplica_grupo == grupo))
            .where(
                or_(
                    RegraValidacao.aplica_subgrupo.is_(None),
                    RegraValidacao.aplica_subgrupo == subgrupo,
                )
            )
            .where(
                or_(
                    RegraValidacao.aplica_modalidade.is_(None),
                    RegraValidacao.aplica_modalidade == modalidade,
                )
            )
            .where(
                or_(
                    RegraValidacao.vigencia_inicio.is_(None),
                    RegraValidacao.vigencia_inicio <= competencia,
                )
            )
            .where(
                or_(
                    RegraValidacao.vigencia_fim.is_(None),
                    RegraValidacao.vigencia_fim >= competencia,
                )
            )
            .order_by(RegraValidacao.codigo)
        )
        return list(self._s.execute(stmt).scalars().all())
