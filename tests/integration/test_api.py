import os
from pathlib import Path

from fastapi.testclient import TestClient

test_db_path = Path("tests/.test.db").resolve()
if test_db_path.exists():
    test_db_path.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path.as_posix()}"

from src.app.main import app  # noqa: E402


def test_health_endpoints() -> None:
    with TestClient(app) as client:
        live_response = client.get("/health/live")
        ready_response = client.get("/health/ready")

        assert live_response.status_code == 200
        assert live_response.json() == {"status": "alive"}
        assert ready_response.status_code == 200
        assert ready_response.json() == {"status": "ready"}


def test_sync_ai_demo_endpoint() -> None:
    with TestClient(app) as client:
        response = client.post("/v1/ai-demo/respond", json={"message": "teste"})

        assert response.status_code == 200
        assert response.json()["provider"] == "mock"
        assert "teste" in response.json()["output"]


def test_async_job_endpoint() -> None:
    with TestClient(app) as client:
        response = client.post("/v1/ai-demo/jobs", json={"message": "job teste"})

        assert response.status_code == 202
        assert response.json()["event_name"] == "ai_demo.requested"
        assert response.json()["status"] == "queued"


def test_user_crud_flow() -> None:
    with TestClient(app) as client:
        create_response = client.post(
            "/v1/users",
            json={
                "name": "Mauricio",
                "email": "mauricio@example.com",
                "password": "Senha123",
                "cpf": "12345678901",
                "cnpj": "12345678000199",
                "cep": "01001000",
                "business": "Enercheck",
            },
        )

        assert create_response.status_code == 201
        created_user = create_response.json()
        assert created_user["name"] == "Mauricio"
        assert created_user["email"] == "mauricio@example.com"
        assert created_user["cpf"] == "12345678901"
        assert created_user["cnpj"] == "12345678000199"
        assert created_user["cep"] == "01001000"
        assert created_user["business"] == "Enercheck"
        assert "password" not in created_user
        user_id = created_user["id"]

        list_response = client.get("/v1/users")
        assert list_response.status_code == 200
        assert any(user["id"] == user_id for user in list_response.json()["items"])

        get_response = client.get(f"/v1/users/{user_id}")
        assert get_response.status_code == 200
        assert get_response.json()["email"] == "mauricio@example.com"

        update_response = client.put(
            f"/v1/users/{user_id}",
            json={
                "name": "Mauricio Silva",
                "email": "mauricio.silva@example.com",
                "password": "Senha456",
                "cpf": "10987654321",
                "cnpj": "98765432000155",
                "cep": "01310930",
                "business": "Enercheck Labs",
            },
        )
        assert update_response.status_code == 200
        assert update_response.json()["name"] == "Mauricio Silva"
        assert update_response.json()["cpf"] == "10987654321"
        assert update_response.json()["cnpj"] == "98765432000155"
        assert update_response.json()["cep"] == "01310930"
        assert update_response.json()["business"] == "Enercheck Labs"

        delete_response = client.delete(f"/v1/users/{user_id}")
        assert delete_response.status_code == 204

        missing_response = client.get(f"/v1/users/{user_id}")
        assert missing_response.status_code == 404
