import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

test_db_path = Path("tests/.test.db").resolve()
if test_db_path.exists():
    test_db_path.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path.as_posix()}"
os.environ["AUTH_SECRET_KEY"] = "test-secret-key"

from src.app.core.config import get_settings  # noqa: E402
from src.app.dependencies import get_container  # noqa: E402
from src.app.main import app  # noqa: E402


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_user(client: TestClient, *, name: str, email: str) -> dict:
    response = client.post(
        "/v1/users",
        json={
            "name": name,
            "email": email,
            "password": "Senha123",
            "cpf": "12345678901",
            "cnpj": "12345678000199",
            "cep": "01001000",
            "business": "Enercheck",
        },
    )
    assert response.status_code == 201
    return response.json()


def login(client: TestClient, *, email: str, password: str = "Senha123") -> dict:
    response = client.post(
        "/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()


@pytest.fixture(autouse=True)
def reset_test_state() -> None:
    get_container.cache_clear()
    get_settings.cache_clear()
    if test_db_path.exists():
        test_db_path.unlink()

    yield

    get_container.cache_clear()
    get_settings.cache_clear()
    if test_db_path.exists():
        test_db_path.unlink()


def test_health_endpoints() -> None:
    with TestClient(app) as client:
        live_response = client.get("/health/live")
        ready_response = client.get("/health/ready")

        assert live_response.status_code == 200
        assert live_response.json() == {"status": "alive"}
        assert ready_response.status_code == 200
        assert ready_response.json() == {"status": "ready"}


def test_sync_ai_demo_endpoint_requires_token() -> None:
    with TestClient(app) as client:
        unauthorized = client.post("/v1/ai-demo/respond", json={"message": "teste"})
        assert unauthorized.status_code == 401

        created_user = create_user(client, name="Admin", email="admin@example.com")
        login_response = login(client, email="admin@example.com")
        response = client.post(
            "/v1/ai-demo/respond",
            json={"message": "teste"},
            headers=auth_header(login_response["access_token"]),
        )

        assert response.status_code == 200
        assert response.json()["provider"] == "mock"
        assert "teste" in response.json()["output"]
        assert created_user["role"] == "admin"


def test_async_job_endpoint_requires_token() -> None:
    with TestClient(app) as client:
        created_user = create_user(client, name="Admin", email="admin@example.com")
        login_response = login(client, email="admin@example.com")

        response = client.post(
            "/v1/ai-demo/jobs",
            json={"message": "job teste"},
            headers=auth_header(login_response["access_token"]),
        )

        assert response.status_code == 202
        assert response.json()["event_name"] == "ai_demo.requested"
        assert response.json()["status"] == "queued"
        assert created_user["id"]


def test_user_auth_and_role_flow() -> None:
    with TestClient(app) as client:
        admin_user = create_user(client, name="Admin", email="admin@example.com")
        normal_user = create_user(client, name="User", email="user@example.com")

        assert admin_user["role"] == "admin"
        assert normal_user["role"] == "user"
        assert admin_user["id"] != normal_user["id"]

        admin_login = login(client, email="admin@example.com")
        user_login = login(client, email="user@example.com")
        admin_token = admin_login["access_token"]
        user_token = user_login["access_token"]

        me_response = client.get("/v1/auth/me", headers=auth_header(user_token))
        assert me_response.status_code == 200
        assert me_response.json()["id"] == normal_user["id"]
        assert me_response.json()["role"] == "user"

        my_user_response = client.get("/v1/users/me", headers=auth_header(user_token))
        assert my_user_response.status_code == 200
        assert my_user_response.json()["id"] == normal_user["id"]

        list_without_token = client.get("/v1/users")
        assert list_without_token.status_code == 401

        list_as_user = client.get("/v1/users", headers=auth_header(user_token))
        assert list_as_user.status_code == 403

        list_as_admin = client.get("/v1/users", headers=auth_header(admin_token))
        assert list_as_admin.status_code == 200
        assert len(list_as_admin.json()["items"]) == 2

        get_other_as_user = client.get(
            f"/v1/users/{admin_user['id']}",
            headers=auth_header(user_token),
        )
        assert get_other_as_user.status_code == 403

        get_self_as_user = client.get(
            f"/v1/users/{normal_user['id']}",
            headers=auth_header(user_token),
        )
        assert get_self_as_user.status_code == 200

        update_response = client.put(
            f"/v1/users/{normal_user['id']}",
            json={
                "name": "User Atualizado",
                "email": "user.updated@example.com",
                "password": "NovaSenha123",
                "cpf": "10987654321",
                "cnpj": "98765432000155",
                "cep": "01310930",
                "business": "Enercheck Labs",
                "role": "admin",
            },
            headers=auth_header(user_token),
        )
        assert update_response.status_code == 200
        assert update_response.json()["name"] == "User Atualizado"
        assert update_response.json()["email"] == "user.updated@example.com"
        assert update_response.json()["role"] == "user"
        assert "password" not in update_response.json()

        user_login_after_update = login(
            client,
            email="user.updated@example.com",
            password="NovaSenha123",
        )
        assert user_login_after_update["user"]["id"] == normal_user["id"]

        delete_other_as_user = client.delete(
            f"/v1/users/{admin_user['id']}",
            headers=auth_header(user_token),
        )
        assert delete_other_as_user.status_code == 403

        admin_promotes_user = client.put(
            f"/v1/users/{normal_user['id']}",
            json={
                "name": "User Atualizado",
                "email": "user.updated@example.com",
                "password": "NovaSenha123",
                "cpf": "10987654321",
                "cnpj": "98765432000155",
                "cep": "01310930",
                "business": "Enercheck Labs",
                "role": "admin",
            },
            headers=auth_header(admin_token),
        )
        assert admin_promotes_user.status_code == 200
        assert admin_promotes_user.json()["role"] == "admin"

        delete_self = client.delete(
            f"/v1/users/{normal_user['id']}",
            headers=auth_header(user_token),
        )
        assert delete_self.status_code == 204

        missing_response = client.get(
            f"/v1/users/{normal_user['id']}",
            headers=auth_header(admin_token),
        )
        assert missing_response.status_code == 404
