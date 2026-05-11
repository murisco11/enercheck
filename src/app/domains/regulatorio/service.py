import uuid
from datetime import date

from sqlalchemy.orm import Session

from src.app.core.exceptions import NaoEncontradoError
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
    BuscaSimilaridadeQuery,
    ChunkCreate,
    DocumentoRegulatorioCreate,
    PacoteRegrasCreate,
    RegraValidacaoCreate,
    SnapshotTarifaCreate,
)


class DocumentoRegulatorioService:
    def __init__(self, session: Session):
        self._repo = DocumentoRegulatorioRepository(session)
        self._session = session

    def criar(self, data: DocumentoRegulatorioCreate) -> DocumentoRegulatorio:
        doc = DocumentoRegulatorio(**data.model_dump())
        self._repo.criar(doc)
        self._session.commit()
        self._session.refresh(doc)
        return doc

    def listar(self) -> list[DocumentoRegulatorio]:
        return self._repo.listar()

    def buscar(self, doc_id: uuid.UUID) -> DocumentoRegulatorio:
        doc = self._repo.buscar_por_id(doc_id)
        if not doc:
            raise NaoEncontradoError("Documento regulatório não encontrado")
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

    def atualizar_embedding(self, chunk_id: uuid.UUID, embedding: list[float]) -> None:
        self._repo.atualizar_embedding(chunk_id, embedding)
        self._session.commit()

    def buscar_similares(
        self, query: BuscaSimilaridadeQuery, embedding: list[float]
    ) -> list[tuple[ChunkRegulatorio, float]]:
        return self._repo.buscar_similares(
            embedding, top_k=query.top_k, documento_id=query.documento_id
        )

    def listar_por_documento(self, documento_id: uuid.UUID) -> list[ChunkRegulatorio]:
        return self._repo.listar_por_documento(documento_id)


class SnapshotTarifaService:
    def __init__(self, session: Session):
        self._repo = SnapshotTarifaRepository(session)
        self._session = session

    def criar(self, data: SnapshotTarifaCreate) -> SnapshotTarifa:
        snap = SnapshotTarifa(**data.model_dump())
        self._repo.criar(snap)
        self._session.commit()
        self._session.refresh(snap)
        return snap

    def buscar_vigente(
        self, distribuidora_id: uuid.UUID, data_referencia: date
    ) -> list[SnapshotTarifa]:
        return self._repo.buscar_vigente(distribuidora_id, data_referencia)

    def deletar(self, snap_id: uuid.UUID, permanente: bool = False) -> None:
        snap = self._session.get(SnapshotTarifa, snap_id)
        if not snap:
            raise NaoEncontradoError("Snapshot de tarifa não encontrado")
        if permanente:
            self._repo.remover(snap)
        else:
            self._repo.desativar(snap)
        self._session.commit()


class PacoteRegrasService:
    def __init__(self, session: Session):
        self._repo = PacoteRegrasRepository(session)
        self._regra_repo = RegraValidacaoRepository(session)
        self._session = session

    def criar(self, data: PacoteRegrasCreate, publicado_por_id: uuid.UUID) -> PacoteRegras:
        pacote = PacoteRegras(**data.model_dump(), publicado_por_id=publicado_por_id)
        self._repo.criar(pacote)
        self._session.commit()
        self._session.refresh(pacote)
        return pacote

    def listar(self) -> list[PacoteRegras]:
        return self._repo.listar()

    def adicionar_regra(self, data: RegraValidacaoCreate) -> RegraValidacao:
        regra = RegraValidacao(**data.model_dump())
        self._regra_repo.criar(regra)
        self._session.commit()
        self._session.refresh(regra)
        return regra

    def listar_regras(
        self, pacote_id: uuid.UUID, apenas_ativas: bool = True
    ) -> list[RegraValidacao]:
        return self._regra_repo.listar_por_pacote(pacote_id, apenas_ativas)

    def deletar_pacote(self, pacote_id: uuid.UUID, permanente: bool = False) -> None:
        pacote = self._session.get(PacoteRegras, pacote_id)
        if not pacote:
            raise NaoEncontradoError("Pacote de regras não encontrado")
        if permanente:
            self._repo.remover(pacote)
        else:
            self._repo.desativar(pacote)
        self._session.commit()

    def deletar_regra(self, regra_id: uuid.UUID, permanente: bool = False) -> None:
        regra = self._regra_repo.buscar_por_id(regra_id)
        if not regra:
            raise NaoEncontradoError("Regra de validação não encontrada")
        if permanente:
            self._regra_repo.remover(regra)
        else:
            self._regra_repo.desativar(regra)
        self._session.commit()
