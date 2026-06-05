import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

test_db_path = Path("tests/.test_general.db").resolve()

os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path.as_posix()}"
os.environ["AUTH_SECRET_KEY"] = "test-secret-general"
os.environ["AUTH_TOKEN_EXPIRE_MINUTES"] = "480"

from src.app.api.v1.dependencies import get_session_manager, get_token_service  # noqa: E402
from src.app.core.config import get_settings  # noqa: E402
from src.app.main import app  # noqa: E402


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def reset_test_state():
    os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path.as_posix()}"
    os.environ["AUTH_SECRET_KEY"] = "test-secret-general"
    os.environ["AUTH_TOKEN_EXPIRE_MINUTES"] = "480"
    get_session_manager.cache_clear()
    get_token_service.cache_clear()
    get_settings.cache_clear()
    if test_db_path.exists():
        test_db_path.unlink()
    yield
    get_session_manager.cache_clear()
    get_token_service.cache_clear()
    get_settings.cache_clear()
    if test_db_path.exists():
        test_db_path.unlink()


def _criar_usuario(client: TestClient, nome: str, email: str, senha: str = "Senha1234") -> dict:
    resp = client.post("/v1/auth/usuarios", json={"nome": nome, "email": email, "senha": senha})
    assert resp.status_code == 201, resp.text
    return resp.json()


def _login(client: TestClient, email: str, senha: str = "Senha1234") -> str:
    resp = client.post("/v1/auth/token", json={"email": email, "senha": senha})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def test_health_endpoints() -> None:
    with TestClient(app) as client:
        live = client.get("/v1/health/live")
        ready = client.get("/v1/health/ready")
        assert live.status_code == 200
        assert live.json() == {"status": "alive"}
        assert ready.status_code == 200
        assert ready.json() == {"status": "ready"}


def test_auth_flow() -> None:
    with TestClient(app) as client:
        admin = _criar_usuario(client, "Admin", "admin@example.com")
        assert admin["papel"] == "admin"
        assert admin["ativo"] is True

        consultor = _criar_usuario(client, "Consultor", "consultor@example.com")
        assert consultor["papel"] == "consultor"

        admin_tok = _login(client, "admin@example.com")
        me = client.get("/v1/auth/me", headers=auth_header(admin_tok))
        assert me.status_code == 200
        assert me.json()["email"] == "admin@example.com"


def test_sem_token_retorna_401() -> None:
    with TestClient(app) as client:
        resp = client.get("/v1/auth/me")
        assert resp.status_code == 401


def test_admin_lista_usuarios() -> None:
    with TestClient(app) as client:
        _criar_usuario(client, "Admin", "admin@example.com")
        _criar_usuario(client, "User", "user@example.com")
        admin_tok = _login(client, "admin@example.com")
        resp = client.get("/v1/auth/usuarios", headers=auth_header(admin_tok))
        assert resp.status_code == 200
        assert len(resp.json()["itens"]) == 2


def test_consultor_nao_lista_usuarios() -> None:
    with TestClient(app) as client:
        _criar_usuario(client, "Admin", "admin@example.com")
        _criar_usuario(client, "User", "user@example.com")
        tok = _login(client, "user@example.com")
        resp = client.get("/v1/auth/usuarios", headers=auth_header(tok))
        assert resp.status_code == 403


def test_soft_delete_impede_login() -> None:
    with TestClient(app) as client:
        user = _criar_usuario(client, "Admin", "admin@example.com")
        tok = _login(client, "admin@example.com")
        client.delete(f"/v1/auth/usuarios/{user['id']}", headers=auth_header(tok))
        resp = client.post(
            "/v1/auth/token", json={"email": "admin@example.com", "senha": "Senha1234"}
        )
        assert resp.status_code == 401


def test_clientes_exige_autenticacao() -> None:
    with TestClient(app) as client:
        resp = client.get("/v1/clientes/")
        assert resp.status_code == 401


def test_admin_cria_cliente() -> None:
    with TestClient(app) as client:
        _criar_usuario(client, "Admin", "admin@example.com")
        tok = _login(client, "admin@example.com")
        resp = client.post(
            "/v1/clientes/",
            json={"razao_social": "Empresa Teste LTDA", "cnpj": "12345678000199"},
            headers=auth_header(tok),
        )
        assert resp.status_code == 201
        assert resp.json()["cnpj"] == "12345678000199"


def test_consultor_nao_cria_cliente() -> None:
    with TestClient(app) as client:
        _criar_usuario(client, "Admin", "admin@example.com")
        _criar_usuario(client, "Consultor", "consultor@example.com")
        tok = _login(client, "consultor@example.com")
        resp = client.post(
            "/v1/clientes/",
            json={"razao_social": "Empresa Teste LTDA", "cnpj": "12345678000199"},
            headers=auth_header(tok),
        )
        assert resp.status_code == 403


def test_fluxo_mvp_crud_fatura_achado_e_recuperacao() -> None:
    with TestClient(app) as client:
        _criar_usuario(client, "Admin", "admin@example.com")
        tok = _login(client, "admin@example.com")
        headers = auth_header(tok)

        dist = client.post(
            "/v1/distribuidoras/",
            json={
                "razao_social": "Distribuidora Teste",
                "cnpj": "11222333000181",
                "sigla": "DST",
                "estado": "SP",
            },
            headers=headers,
        )
        assert dist.status_code == 201, dist.text
        distribuidora_id = dist.json()["id"]

        cliente = client.post(
            "/v1/clientes/",
            json={"razao_social": "Industria Teste LTDA", "cnpj": "12345678000199"},
            headers=headers,
        )
        assert cliente.status_code == 201, cliente.text
        cliente_id = cliente.json()["id"]

        uc = client.post(
            f"/v1/clientes/{cliente_id}/ucs",
            json={
                "distribuidora_id": distribuidora_id,
                "codigo_instalacao": "UC-001",
                "grupo": "A",
                "subgrupo": "A4",
                "modalidade": "verde",
                "cidade": "Sao Paulo",
                "estado": "SP",
            },
            headers=headers,
        )
        assert uc.status_code == 201, uc.text
        uc_id = uc.json()["id"]

        pacote = client.post(
            "/v1/regulatorio/regras/pacotes",
            json={"versao": "2025.1", "descricao": "Pacote teste", "vigente": True},
            headers=headers,
        )
        assert pacote.status_code == 201, pacote.text
        pacote_id = pacote.json()["id"]

        snapshot = client.post(
            "/v1/regulatorio/tarifas/snapshots",
            json={
                "distribuidora_id": distribuidora_id,
                "grupo": "A",
                "subgrupo": "A4",
                "modalidade": "verde",
                "vigencia_inicio": "2025-01-01",
                "valor_tusd": "0.50",
                "valor_te": "0.30",
                "valor_tusd_com_tributos": "0.50",
                "valor_te_com_tributos": "0.30",
                "adicional_bandeira": "0",
            },
            headers=headers,
        )
        assert snapshot.status_code == 201, snapshot.text

        regra = client.post(
            "/v1/regulatorio/regras",
            json={
                "pacote_regras_id": pacote_id,
                "codigo": "TAR-TUSD-001",
                "nome": "Tarifa TUSD homologada",
                "categoria": "tarifa",
                "severidade": "alta",
                "expressao_logica": {
                    "tipo": "tarifa_item",
                    "tipo_item": "tusd",
                    "campo_snapshot": "valor_tusd",
                },
                "ativa": True,
            },
            headers=headers,
        )
        assert regra.status_code == 201, regra.text

        fatura = client.post(
            "/v1/faturas/",
            json={
                "unidade_consumidora_id": uc_id,
                "competencia": "2025-01",
                "data_emissao": "2025-01-10",
                "valor_total": "100.00",
                "modalidade": "verde",
                "base_leitura": "real",
                "medidas": [
                    {
                        "posto_horario": "unico",
                        "leitura_anterior": "0",
                        "leitura_atual": "100",
                        "constante_medidor": "1",
                        "consumo_kwh": "100",
                    }
                ],
                "itens": [
                    {
                        "tipo_item": "tusd",
                        "descricao": "TUSD consumo",
                        "quantidade": "100",
                        "tarifa_unitaria": "0.60",
                        "valor": "60.00",
                    },
                    {
                        "tipo_item": "outro",
                        "descricao": "Outras cobrancas",
                        "quantidade": "1",
                        "tarifa_unitaria": "40",
                        "valor": "40.00",
                    },
                ],
            },
            headers=headers,
        )
        assert fatura.status_code == 201, fatura.text
        fatura_id = fatura.json()["id"]

        achado = client.post(
            "/v1/achados/",
            json={
                "fatura_id": fatura_id,
                "titulo": "Tarifa TUSD acima do esperado",
                "descricao": "Achado manual para exercitar CRUD de recuperação.",
                "categoria": "tarifa",
                "severidade": "alta",
                "valor_cobrado_a_maior": "10.00",
            },
            headers=headers,
        )
        assert achado.status_code == 201, achado.text
        achado_id = achado.json()["id"]

        achado_confirmado = client.patch(
            f"/v1/achados/{achado_id}",
            json={"status": "confirmado"},
            headers=headers,
        )
        assert achado_confirmado.status_code == 200, achado_confirmado.text

        caso = client.post(
            "/v1/recuperacao/casos",
            json={
                "cliente_id": cliente_id,
                "unidade_consumidora_id": uc_id,
                "prioridade": "alta",
            },
            headers=headers,
        )
        assert caso.status_code == 201, caso.text
        caso_id = caso.json()["id"]

        item = client.post(
            f"/v1/recuperacao/casos/{caso_id}/itens",
            json={
                "achado_id": achado_id,
                "fatura_id": fatura_id,
                "valor_cobrado_a_maior": "10.00",
                "valor_recuperavel": "10.00",
            },
            headers=headers,
        )
        assert item.status_code == 201, item.text

        caso_atualizado = client.get(f"/v1/recuperacao/casos/{caso_id}", headers=headers)
        assert caso_atualizado.status_code == 200, caso_atualizado.text
        assert caso_atualizado.json()["total_estimado"] in ["10.00", 10.0, 10]
