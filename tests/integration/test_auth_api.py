import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

test_db_path = Path("tests/.test_auth.db").resolve()

os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path.as_posix()}"
os.environ["AUTH_SECRET_KEY"] = "test-secret-key-auth"
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


def _login(client: TestClient, email: str, senha: str = "Senha1234") -> dict:
    resp = client.post("/v1/auth/token", json={"email": email, "senha": senha})
    assert resp.status_code == 200, resp.text
    return resp.json()


class TestBootstrap:
    def test_primeiro_usuario_vira_admin(self):
        with TestClient(app) as client:
            user = _criar_usuario(client, "Admin", "admin@test.com")
            assert user["papel"] == "admin"
            assert user["ativo"] is True

    def test_segundo_usuario_vira_consultor(self):
        with TestClient(app) as client:
            _criar_usuario(client, "Admin", "admin@test.com")
            user = _criar_usuario(client, "Consultor", "consultor@test.com")
            assert user["papel"] == "consultor"

    def test_email_duplicado_retorna_409(self):
        with TestClient(app) as client:
            _criar_usuario(client, "Admin", "admin@test.com")
            resp = client.post(
                "/v1/auth/usuarios",
                json={"nome": "Outro", "email": "admin@test.com", "senha": "Senha1234"},
            )
            assert resp.status_code == 409


class TestLogin:
    def test_login_bem_sucedido(self):
        with TestClient(app) as client:
            _criar_usuario(client, "Admin", "admin@test.com")
            resp = client.post(
                "/v1/auth/token", json={"email": "admin@test.com", "senha": "Senha1234"}
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"
            assert "expires_in" in data
            assert data["usuario"]["email"] == "admin@test.com"

    def test_login_senha_errada_retorna_401(self):
        with TestClient(app) as client:
            _criar_usuario(client, "Admin", "admin@test.com")
            resp = client.post(
                "/v1/auth/token", json={"email": "admin@test.com", "senha": "SenhaErrada9"}
            )
            assert resp.status_code == 401

    def test_login_email_inexistente_retorna_401(self):
        with TestClient(app) as client:
            resp = client.post(
                "/v1/auth/token", json={"email": "nao@existe.com", "senha": "Senha1234"}
            )
            assert resp.status_code == 401

    def test_usuario_inativo_nao_consegue_login(self):
        with TestClient(app) as client:
            user = _criar_usuario(client, "Admin", "admin@test.com")
            tok = _login(client, "admin@test.com")["access_token"]
            client.delete(f"/v1/auth/usuarios/{user['id']}", headers=auth_header(tok))
            resp = client.post(
                "/v1/auth/token", json={"email": "admin@test.com", "senha": "Senha1234"}
            )
            assert resp.status_code == 401


class TestMe:
    def test_me_com_token_valido(self):
        with TestClient(app) as client:
            user = _criar_usuario(client, "Admin", "admin@test.com")
            tok = _login(client, "admin@test.com")["access_token"]
            resp = client.get("/v1/auth/me", headers=auth_header(tok))
            assert resp.status_code == 200
            assert resp.json()["id"] == user["id"]
            assert resp.json()["email"] == "admin@test.com"

    def test_me_sem_token_retorna_401(self):
        with TestClient(app) as client:
            resp = client.get("/v1/auth/me")
            assert resp.status_code == 401

    def test_me_token_invalido_retorna_401(self):
        with TestClient(app) as client:
            resp = client.get("/v1/auth/me", headers=auth_header("token.invalido"))
            assert resp.status_code == 401


class TestUsuariosAdmin:
    def test_listar_usuarios_exige_admin(self):
        with TestClient(app) as client:
            _criar_usuario(client, "Admin", "admin@test.com")
            _criar_usuario(client, "Consultor", "consultor@test.com")
            admin_tok = _login(client, "admin@test.com")["access_token"]
            consultor_tok = _login(client, "consultor@test.com")["access_token"]

            resp = client.get("/v1/auth/usuarios", headers=auth_header(admin_tok))
            assert resp.status_code == 200
            assert len(resp.json()["itens"]) == 2

            resp = client.get("/v1/auth/usuarios", headers=auth_header(consultor_tok))
            assert resp.status_code == 403

    def test_obter_usuario_por_id_proprio(self):
        with TestClient(app) as client:
            user = _criar_usuario(client, "Admin", "admin@test.com")
            tok = _login(client, "admin@test.com")["access_token"]
            resp = client.get(f"/v1/auth/usuarios/{user['id']}", headers=auth_header(tok))
            assert resp.status_code == 200

    def test_obter_usuario_outro_usuario_como_consultor_retorna_403(self):
        with TestClient(app) as client:
            admin = _criar_usuario(client, "Admin", "admin@test.com")
            _criar_usuario(client, "Consultor", "consultor@test.com")
            consultor_tok = _login(client, "consultor@test.com")["access_token"]
            resp = client.get(f"/v1/auth/usuarios/{admin['id']}", headers=auth_header(consultor_tok))
            assert resp.status_code == 403


class TestPatchUsuario:
    def test_patch_nome(self):
        with TestClient(app) as client:
            user = _criar_usuario(client, "Admin", "admin@test.com")
            tok = _login(client, "admin@test.com")["access_token"]
            resp = client.patch(
                f"/v1/auth/usuarios/{user['id']}",
                json={"nome": "Novo Nome"},
                headers=auth_header(tok),
            )
            assert resp.status_code == 200
            assert resp.json()["nome"] == "Novo Nome"

    def test_consultor_nao_pode_mudar_proprio_papel(self):
        with TestClient(app) as client:
            _criar_usuario(client, "Admin", "admin@test.com")
            user = _criar_usuario(client, "Consultor", "consultor@test.com")
            tok = _login(client, "consultor@test.com")["access_token"]
            resp = client.patch(
                f"/v1/auth/usuarios/{user['id']}",
                json={"papel": "admin"},
                headers=auth_header(tok),
            )
            assert resp.status_code == 200
            assert resp.json()["papel"] == "consultor"

    def test_admin_pode_mudar_papel_de_outro(self):
        with TestClient(app) as client:
            _criar_usuario(client, "Admin", "admin@test.com")
            user = _criar_usuario(client, "Consultor", "consultor@test.com")
            admin_tok = _login(client, "admin@test.com")["access_token"]
            resp = client.patch(
                f"/v1/auth/usuarios/{user['id']}",
                json={"papel": "visualizador"},
                headers=auth_header(admin_tok),
            )
            assert resp.status_code == 200
            assert resp.json()["papel"] == "visualizador"


class TestDesativarUsuario:
    def test_desativar_retorna_204_e_impede_login(self):
        with TestClient(app) as client:
            user = _criar_usuario(client, "Admin", "admin@test.com")
            tok = _login(client, "admin@test.com")["access_token"]
            resp = client.delete(f"/v1/auth/usuarios/{user['id']}", headers=auth_header(tok))
            assert resp.status_code == 204

            resp = client.post(
                "/v1/auth/token", json={"email": "admin@test.com", "senha": "Senha1234"}
            )
            assert resp.status_code == 401

    def test_consultor_nao_pode_desativar_outro(self):
        with TestClient(app) as client:
            admin = _criar_usuario(client, "Admin", "admin@test.com")
            _criar_usuario(client, "Consultor", "consultor@test.com")
            consultor_tok = _login(client, "consultor@test.com")["access_token"]
            resp = client.delete(
                f"/v1/auth/usuarios/{admin['id']}", headers=auth_header(consultor_tok)
            )
            assert resp.status_code == 403
