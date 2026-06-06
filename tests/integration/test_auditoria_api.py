"""Integração do motor de validação: seed regulatório + fatura → POST validação →
achado quantificado. Cobre também a sinalização de duplicidade lógica."""

import os
import tempfile
import uuid
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

test_db_path = Path("tests/.test_auditoria.db").resolve()
test_storage_dir = Path(tempfile.gettempdir()) / "enercheck_test_storage"

os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path.as_posix()}"
os.environ["AUTH_SECRET_KEY"] = "test-secret-key-auditoria"
os.environ["STORAGE_DIR"] = str(test_storage_dir)

from sqlalchemy import select  # noqa: E402

from scripts.seed import seed  # noqa: E402
from src.app.api.v1.dependencies import (  # noqa: E402
    get_session_manager,
    get_token_service,
)
from src.app.core.config import get_settings  # noqa: E402
from src.app.core.enums import (  # noqa: E402
    BaseLeitura,
    ModalidadeTarifaria,
    PostoHorario,
    TipoItem,
)
from src.app.core.storage import get_object_storage  # noqa: E402
from src.app.domains.clientes.models import Cliente, Distribuidora, UnidadeConsumidora  # noqa: E402
from src.app.domains.documental.duplicidade import sinalizar_duplicidade  # noqa: E402
from src.app.domains.faturas.models import Fatura, ItemFatura, MedidaFatura  # noqa: E402
from src.app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def reset_state():
    os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path.as_posix()}"
    os.environ["AUTH_SECRET_KEY"] = "test-secret-key-auditoria"
    os.environ["STORAGE_DIR"] = str(test_storage_dir)
    for cache in (get_session_manager, get_token_service, get_settings, get_object_storage):
        cache.cache_clear()
    if test_db_path.exists():
        test_db_path.unlink()
    yield
    for cache in (get_session_manager, get_token_service, get_settings, get_object_storage):
        cache.cache_clear()
    if test_db_path.exists():
        test_db_path.unlink()


def _pdf_sample(nome: str) -> Path | None:
    base = Path(os.environ.get("SAMPLE_PDF_DIR", str(Path.home() / "Downloads")))
    caminho = base / nome
    return caminho if caminho.exists() else None


def _admin(client: TestClient) -> str:
    client.post(
        "/v1/auth/usuarios",
        json={"nome": "Admin", "email": "admin@test.com", "senha": "Senha1234"},
    )
    resp = client.post("/v1/auth/token", json={"email": "admin@test.com", "senha": "Senha1234"})
    return resp.json()["access_token"]


def _cosern_id(db) -> uuid.UUID:
    return db.scalar(select(Distribuidora.id).where(Distribuidora.cnpj == "08324196000181"))


def _criar_uc(db, distribuidora_id: uuid.UUID) -> UnidadeConsumidora:
    cliente = Cliente(razao_social="Cliente Teste", cnpj="11111111111111")
    db.add(cliente)
    db.flush()
    uc = UnidadeConsumidora(
        cliente_id=cliente.id,
        distribuidora_id=distribuidora_id,
        codigo_instalacao="123",
        grupo="B",
        subgrupo="B1",
        modalidade=ModalidadeTarifaria.CONVENCIONAL,
        cidade="Natal",
        estado="RN",
    )
    db.add(uc)
    db.flush()
    return uc


def _criar_fatura(db, uc_id: uuid.UUID, *, competencia: str, tarifa_tusd: str) -> Fatura:
    fatura = Fatura(
        unidade_consumidora_id=uc_id,
        competencia=competencia,
        valor_total=Decimal("100.00"),
        modalidade=ModalidadeTarifaria.CONVENCIONAL,
        base_leitura=BaseLeitura.REAL,
    )
    fatura.medidas = [
        MedidaFatura(
            leitura_anterior=Decimal("1000"),
            leitura_atual=Decimal("1100"),
            constante_medidor=Decimal("1"),
            consumo_kwh=Decimal("100"),
            posto_horario=PostoHorario.UNICO,
        )
    ]
    fatura.itens = [
        ItemFatura(
            tipo_item=TipoItem.TUSD,
            descricao="Consumo-TUSD",
            quantidade=Decimal("100"),
            tarifa_unitaria=Decimal(tarifa_tusd),
            valor=(Decimal("100") * Decimal(tarifa_tusd)),
        )
    ]
    db.add(fatura)
    db.flush()
    return fatura


class TestValidacaoFatura:
    def test_validacao_detecta_cobranca_a_maior(self):
        with TestClient(app) as client:
            token = _admin(client)
            mgr = get_session_manager()
            with mgr.session_factory() as db:
                seed(db)
                uc = _criar_uc(db, _cosern_id(db))
                # TUSD cobrada a 0,70; snapshot 2025 é 0,57422746 -> cobrança a maior.
                fatura = _criar_fatura(db, uc.id, competencia="2025-11", tarifa_tusd="0.70")
                db.commit()
                fatura_id = str(fatura.id)

            resp = client.post(
                f"/v1/faturas/{fatura_id}/validacoes",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 201, resp.text
            corpo = resp.json()
            assert corpo["status"] == "concluido"
            assert corpo["total_achados"] >= 1
            assert Decimal(corpo["valor_total_cobrado_a_maior"]) > 0
            achados_tusd = [a for a in corpo["achados"] if a["valor_cobrado_a_maior"] != "0.00"]
            assert achados_tusd, corpo["achados"]

    def test_validacao_fatura_correta_sem_achado_monetario(self):
        with TestClient(app) as client:
            token = _admin(client)
            mgr = get_session_manager()
            with mgr.session_factory() as db:
                seed(db)
                uc = _criar_uc(db, _cosern_id(db))
                fatura = _criar_fatura(db, uc.id, competencia="2025-11", tarifa_tusd="0.57422746")
                db.commit()
                fatura_id = str(fatura.id)

            resp = client.post(
                f"/v1/faturas/{fatura_id}/validacoes",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 201, resp.text
            assert Decimal(resp.json()["valor_total_cobrado_a_maior"]) == 0


class TestDuplicidade:
    def test_sinaliza_duplicata_logica(self):
        with TestClient(app):
            mgr = get_session_manager()
            with mgr.session_factory() as db:
                seed(db)
                uc = _criar_uc(db, _cosern_id(db))
                _criar_fatura(db, uc.id, competencia="2025-11", tarifa_tusd="0.57")
                segunda = _criar_fatura(db, uc.id, competencia="2025-11", tarifa_tusd="0.57")
                db.commit()
                achado = sinalizar_duplicidade(db, segunda)
                assert achado is not None
                assert achado.categoria.value == "duplicidade"

    def test_sem_duplicata_nao_sinaliza(self):
        with TestClient(app):
            mgr = get_session_manager()
            with mgr.session_factory() as db:
                seed(db)
                uc = _criar_uc(db, _cosern_id(db))
                unica = _criar_fatura(db, uc.id, competencia="2025-10", tarifa_tusd="0.57")
                db.commit()
                assert sinalizar_duplicidade(db, unica) is None


class TestUploadReal:
    def test_upload_extrai_e_persiste_fatura(self):
        pdf = _pdf_sample("COSERN - 01.22.pdf")
        if pdf is None:
            pytest.skip("PDF de exemplo 2022 ausente.")
        with TestClient(app) as client:
            token = _admin(client)
            headers = {"Authorization": f"Bearer {token}"}
            mgr = get_session_manager()
            with mgr.session_factory() as db:
                seed(db)
                uc = _criar_uc(db, _cosern_id(db))
                db.commit()
                uc_id = str(uc.id)

            # Upload (a extração roda em background, síncrona no TestClient).
            resp = client.post(
                "/v1/documental/documentos/upload",
                data={"unidade_consumidora_id": uc_id},
                files={"arquivo": ("COSERN - 01.22.pdf", pdf.read_bytes(), "application/pdf")},
                headers=headers,
            )
            assert resp.status_code == 201, resp.text
            doc_id = resp.json()["id"]

            doc = client.get(f"/v1/documental/documentos/{doc_id}", headers=headers).json()
            assert doc["status_extracao"] == "concluido", doc.get("erro_extracao")

            faturas = client.get(
                "/v1/faturas", params={"unidade_consumidora_id": uc_id}, headers=headers
            ).json()
            assert faturas["total"] == 1
            assert faturas["itens"][0]["competencia"] == "2021-12"

            # Reenvio do mesmo arquivo -> duplicata exata bloqueada (409).
            resp2 = client.post(
                "/v1/documental/documentos/upload",
                data={"unidade_consumidora_id": uc_id},
                files={"arquivo": ("COSERN - 01.22.pdf", pdf.read_bytes(), "application/pdf")},
                headers=headers,
            )
            assert resp2.status_code == 409, resp2.text
