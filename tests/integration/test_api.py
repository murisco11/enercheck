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
