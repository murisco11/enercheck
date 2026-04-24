from fastapi.testclient import TestClient

from src.app.main import app

client = TestClient(app)


def test_health_endpoints() -> None:
    live_response = client.get("/health/live")
    ready_response = client.get("/health/ready")

    assert live_response.status_code == 200
    assert live_response.json() == {"status": "alive"}
    assert ready_response.status_code == 200
    assert ready_response.json() == {"status": "ready"}


def test_sync_ai_demo_endpoint() -> None:
    response = client.post("/v1/ai-demo/respond", json={"message": "teste"})

    assert response.status_code == 200
    assert response.json()["provider"] == "mock"
    assert "teste" in response.json()["output"]


def test_async_job_endpoint() -> None:
    response = client.post("/v1/ai-demo/jobs", json={"message": "job teste"})

    assert response.status_code == 202
    assert response.json()["event_name"] == "ai_demo.requested"
    assert response.json()["status"] == "queued"
