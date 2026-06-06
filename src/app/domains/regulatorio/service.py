import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.app.core.enums import Grupo, ModalidadeTarifaria, PostoHorario, Subgrupo
from src.app.core.exceptions import ConflitoDuplicidadeError, NaoEncontradoError, RegraVioladaError
from src.app.domains.clientes.repository import DistribuidoraRepository
from src.app.domains.regulatorio.models import (
    ChunkRegulatorio,
    DocumentoRegulatorio,
    PacoteRegras,
    RegraValidacao,
    SnapshotTarifa,
)
from src.app.domains.regulatorio.repository import (
    ChunkRegulatorioRepository,
    DocumentoRegulatorioRepository,
    PacoteRegrasRepository,
    RegraValidacaoRepository,
    SnapshotTarifaRepository,
)
from src.app.domains.regulatorio.schemas import (
    ChunkCreate,
    DocumentoRegulatorioCreate,
    DocumentoRegulatorioUpdate,
    PacoteRegrasCreate,
    PacoteRegrasUpdate,
    RegraValidacaoCreate,
    RegraValidacaoUpdate,
    SnapshotTarifaCreate,
    SnapshotTarifaUpdate,
)


def competencia_para_data(competencia: str) -> date:
    """'YYYY-MM' -> primeiro dia do mês (referência de vigência)."""
    ano, mes = competencia.split("-")
    return date(int(ano), int(mes), 1)


@dataclass(frozen=True)
class ContextoRegulatorio:
    """Tudo o que o motor determinístico precisa para validar uma fatura."""

    pacote: PacoteRegras
    snapshot: SnapshotTarifa | None
    regras: list[RegraValidacao]


class ResolucaoService:
    """Resolve, por vigência, o pacote de regras, o snapshot tarifário e as regras
    aplicáveis a uma fatura — a ponte entre o repositório regulatório e o motor."""

    def __init__(self, session: Session):
        self._pacotes = PacoteRegrasRepository(session)
        self._snapshots = SnapshotTarifaRepository(session)
        self._regras = RegraValidacaoRepository(session)

    def resolver_contexto(
        self,
        *,
        distribuidora_id: uuid.UUID,
        grupo: Grupo,
        subgrupo: Subgrupo,
        modalidade: ModalidadeTarifaria,
        competencia: str,
        posto: PostoHorario | None = None,
    ) -> ContextoRegulatorio:
        pacote = self._pacotes.buscar_vigente()
        if pacote is None:
            raise RegraVioladaError(
                "Nenhum pacote de regras vigente: publique um pacote antes de validar."
            )
        ref = competencia_para_data(competencia)
        snapshot = self._snapshots.resolver(
            distribuidora_id=distribuidora_id,
            grupo=grupo,
            subgrupo=subgrupo,
            modalidade=modalidade,
            competencia=ref,
            posto=posto,
        )
        regras = self._regras.listar_aplicaveis(
            pacote.id,
            grupo=grupo,
            subgrupo=subgrupo,
            modalidade=modalidade,
            competencia=ref,
        )
        return ContextoRegulatorio(pacote=pacote, snapshot=snapshot, regras=regras)


class DocumentoRegulatorioService:
    def __init__(self, session: Session):
        self._repo = DocumentoRegulatorioRepository(session)
        self._session = session

    def criar(self, data: DocumentoRegulatorioCreate) -> DocumentoRegulatorio:
        doc = DocumentoRegulatorio(**data.model_dump())
        try:
            self._repo.criar(doc)
            self._session.commit()
            self._session.refresh(doc)
        except IntegrityError as exc:
            self._session.rollback()
            raise ConflitoDuplicidadeError(
                "Já existe um documento regulatório com este identificador."
            ) from exc
        return doc

    def listar(self) -> list[DocumentoRegulatorio]:
        return self._repo.listar()

    def buscar(self, doc_id: uuid.UUID) -> DocumentoRegulatorio:
        doc = self._repo.buscar_por_id(doc_id)
        if not doc:
            raise NaoEncontradoError("Documento regulatório não encontrado")
        return doc

    def atualizar(
        self, doc_id: uuid.UUID, data: DocumentoRegulatorioUpdate
    ) -> DocumentoRegulatorio:
        doc = self.buscar(doc_id)
        inicio = data.vigencia_inicio or doc.vigencia_inicio
        fim = data.vigencia_fim if "vigencia_fim" in data.model_fields_set else doc.vigencia_fim
        if fim is not None and fim < inicio:
            raise RegraVioladaError("vigencia_fim deve ser igual ou posterior a vigencia_inicio.")
        try:
            self._repo.atualizar(doc, data)
            self._session.commit()
            self._session.refresh(doc)
        except IntegrityError as exc:
            self._session.rollback()
            raise ConflitoDuplicidadeError(
                "Já existe um documento regulatório com este identificador."
            ) from exc
        return doc

    def deletar(self, doc_id: uuid.UUID, permanente: bool = False) -> None:
        doc = self.buscar(doc_id)
        if permanente:
            self._repo.remover(doc)
        else:
            self._repo.desativar(doc)
        self._session.commit()


class ChunkService:
    def __init__(self, session: Session):
        self._repo = ChunkRegulatorioRepository(session)
        self._doc_repo = DocumentoRegulatorioRepository(session)
        self._session = session

    def adicionar_chunks(
        self, documento_id: uuid.UUID, chunks_data: list[ChunkCreate]
    ) -> list[ChunkRegulatorio]:
        if not self._doc_repo.buscar_por_id(documento_id):
            raise NaoEncontradoError("Documento regulatório não encontrado")
        chunks = [
            ChunkRegulatorio(documento_regulatorio_id=documento_id, **c.model_dump())
            for c in chunks_data
        ]
        self._repo.criar_lote(chunks)
        self._session.commit()
        return chunks

    def listar_por_documento(self, documento_id: uuid.UUID) -> list[ChunkRegulatorio]:
        return self._repo.listar_por_documento(documento_id)


class SnapshotTarifaService:
    def __init__(self, session: Session):
        self._repo = SnapshotTarifaRepository(session)
        self._doc_repo = DocumentoRegulatorioRepository(session)
        self._dist_repo = DistribuidoraRepository(session)
        self._session = session

    def criar(self, data: SnapshotTarifaCreate) -> SnapshotTarifa:
        self._validar_referencias(data.distribuidora_id, data.documento_origem_id)
        snap = SnapshotTarifa(**data.model_dump())
        if self._repo.existe_sobreposicao(snap):
            raise RegraVioladaError("Já existe snapshot ativo com vigência sobreposta.")
        self._repo.criar(snap)
        self._session.commit()
        self._session.refresh(snap)
        return snap

    def listar(self, distribuidora_id: uuid.UUID | None = None) -> list[SnapshotTarifa]:
        return self._repo.listar(distribuidora_id=distribuidora_id)

    def buscar(self, snap_id: uuid.UUID) -> SnapshotTarifa:
        snap = self._repo.buscar_por_id(snap_id)
        if not snap:
            raise NaoEncontradoError("Snapshot de tarifa não encontrado")
        return snap

    def atualizar(self, snap_id: uuid.UUID, data: SnapshotTarifaUpdate) -> SnapshotTarifa:
        snap = self.buscar(snap_id)
        documento_id = (
            data.documento_origem_id
            if "documento_origem_id" in data.model_fields_set
            else snap.documento_origem_id
        )
        self._validar_referencias(snap.distribuidora_id, documento_id)
        inicio = data.vigencia_inicio or snap.vigencia_inicio
        fim = data.vigencia_fim if "vigencia_fim" in data.model_fields_set else snap.vigencia_fim
        if fim is not None and fim < inicio:
            raise RegraVioladaError("vigencia_fim deve ser igual ou posterior a vigencia_inicio.")
        self._repo.atualizar(snap, data)
        if self._repo.existe_sobreposicao(snap, ignorar_id=snap.id):
            self._session.rollback()
            raise RegraVioladaError("Já existe snapshot ativo com vigência sobreposta.")
        self._session.commit()
        self._session.refresh(snap)
        return snap

    def deletar(self, snap_id: uuid.UUID, permanente: bool = False) -> None:
        snap = self.buscar(snap_id)
        if permanente:
            self._repo.remover(snap)
        else:
            self._repo.desativar(snap)
        self._session.commit()

    def _validar_referencias(
        self, distribuidora_id: uuid.UUID, documento_origem_id: uuid.UUID | None
    ) -> None:
        if self._dist_repo.buscar_por_id(distribuidora_id) is None:
            raise NaoEncontradoError("Distribuidora não encontrada.")
        if documento_origem_id is not None and self._doc_repo.buscar_por_id(
            documento_origem_id
        ) is None:
            raise NaoEncontradoError("Documento regulatório não encontrado.")


class PacoteRegrasService:
    def __init__(self, session: Session):
        self._repo = PacoteRegrasRepository(session)
        self._regra_repo = RegraValidacaoRepository(session)
        self._doc_repo = DocumentoRegulatorioRepository(session)
        self._session = session

    def criar(self, data: PacoteRegrasCreate, publicado_por_id: uuid.UUID) -> PacoteRegras:
        pacote = PacoteRegras(**data.model_dump(), publicado_por_id=publicado_por_id)
        try:
            if pacote.vigente:
                self._repo.limpar_vigente()
            self._repo.criar(pacote)
            self._session.commit()
            self._session.refresh(pacote)
        except IntegrityError as exc:
            self._session.rollback()
            raise ConflitoDuplicidadeError("Já existe um pacote com esta versão.") from exc
        return pacote

    def listar(self) -> list[PacoteRegras]:
        return self._repo.listar()

    def buscar(self, pacote_id: uuid.UUID) -> PacoteRegras:
        pacote = self._repo.buscar_por_id(pacote_id)
        if not pacote:
            raise NaoEncontradoError("Pacote de regras não encontrado")
        return pacote

    def atualizar(self, pacote_id: uuid.UUID, data: PacoteRegrasUpdate) -> PacoteRegras:
        pacote = self.buscar(pacote_id)
        try:
            if data.vigente is True:
                self._repo.limpar_vigente(exceto_id=pacote.id)
            self._repo.atualizar(pacote, data)
            self._session.commit()
            self._session.refresh(pacote)
        except IntegrityError as exc:
            self._session.rollback()
            raise ConflitoDuplicidadeError("Já existe um pacote com esta versão.") from exc
        return pacote

    def adicionar_regra(self, data: RegraValidacaoCreate) -> RegraValidacao:
        self._validar_referencias_regra(data.pacote_regras_id, data.documento_origem_id)
        regra = RegraValidacao(**data.model_dump())
        try:
            self._regra_repo.criar(regra)
            self._session.commit()
            self._session.refresh(regra)
        except IntegrityError as exc:
            self._session.rollback()
            raise ConflitoDuplicidadeError("Já existe uma regra com este código.") from exc
        return regra

    def listar_regras(
        self, pacote_id: uuid.UUID, apenas_ativas: bool = True
    ) -> list[RegraValidacao]:
        self.buscar(pacote_id)
        return self._regra_repo.listar_por_pacote(pacote_id, apenas_ativas)

    def buscar_regra(self, regra_id: uuid.UUID) -> RegraValidacao:
        regra = self._regra_repo.buscar_por_id(regra_id)
        if not regra:
            raise NaoEncontradoError("Regra de validação não encontrada")
        return regra

    def atualizar_regra(self, regra_id: uuid.UUID, data: RegraValidacaoUpdate) -> RegraValidacao:
        regra = self.buscar_regra(regra_id)
        pacote_id = data.pacote_regras_id or regra.pacote_regras_id
        documento_id = (
            data.documento_origem_id
            if "documento_origem_id" in data.model_fields_set
            else regra.documento_origem_id
        )
        self._validar_referencias_regra(pacote_id, documento_id)
        inicio = data.vigencia_inicio or regra.vigencia_inicio
        fim = data.vigencia_fim if "vigencia_fim" in data.model_fields_set else regra.vigencia_fim
        if fim is not None and inicio is None:
            raise RegraVioladaError(
                "vigencia_inicio é obrigatória quando vigencia_fim é informada."
            )
        if inicio is not None and fim is not None and fim < inicio:
            raise RegraVioladaError("vigencia_fim deve ser igual ou posterior a vigencia_inicio.")
        try:
            self._regra_repo.atualizar(regra, data)
            self._session.commit()
            self._session.refresh(regra)
        except IntegrityError as exc:
            self._session.rollback()
            raise ConflitoDuplicidadeError("Já existe uma regra com este código.") from exc
        return regra

    def deletar_pacote(self, pacote_id: uuid.UUID, permanente: bool = False) -> None:
        pacote = self.buscar(pacote_id)
        if permanente:
            self._repo.remover(pacote)
        else:
            self._repo.desativar(pacote)
        self._session.commit()

    def deletar_regra(self, regra_id: uuid.UUID, permanente: bool = False) -> None:
        regra = self.buscar_regra(regra_id)
        if permanente:
            self._regra_repo.remover(regra)
        else:
            self._regra_repo.desativar(regra)
        self._session.commit()

    def _validar_referencias_regra(
        self, pacote_id: uuid.UUID, documento_origem_id: uuid.UUID | None
    ) -> None:
        if self._repo.buscar_por_id(pacote_id) is None:
            raise NaoEncontradoError("Pacote de regras não encontrado")
        if documento_origem_id is not None and self._doc_repo.buscar_por_id(
            documento_origem_id
        ) is None:
            raise NaoEncontradoError("Documento regulatório não encontrado")
