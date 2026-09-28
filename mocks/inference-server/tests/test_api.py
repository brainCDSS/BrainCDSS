from fastapi.testclient import TestClient
import pytest
from main import app

client = TestClient(app)
ANALYSIS_ID = "00000000-0000-0000-0000-000000000001"


@pytest.fixture(autouse=True)
def enable_mock(monkeypatch):
    monkeypatch.setenv("INFERENCE_MOCK_ENABLED", "true")


def test_health_and_ready():
    assert client.get("/health").json() == {
        "status": "ok", "service": "inference-mock", "is_mock": True,
    }
    assert client.get("/ready").json() == {
        "status": "ready", "mode": "MOCK", "is_mock": True, "model_configured": False,
    }


def test_success_contract():
    response = client.post("/mock/inference", json={"analysis_id": ANALYSIS_ID})
    assert response.status_code == 200
    assert response.json() == {
        "analysis_id": ANALYSIS_ID, "mode": "MOCK", "is_mock": True,
        "accuracy_simulated": False, "status": "SUCCEEDED",
        "result": {"message": "Synthetic pipeline verification only"},
    }


def test_failure_contract():
    response = client.post("/mock/inference", json={"analysis_id": ANALYSIS_ID, "outcome": "failure"})
    assert response.status_code == 500
    assert response.json() == {"detail": "MOCK_INFERENCE_FAILED"}


@pytest.mark.parametrize("payload", [
    {"analysis_id": "invalid"},
    {"analysis_id": ANALYSIS_ID, "outcome": "invalid"},
    {"analysis_id": ANALYSIS_ID, "extra": "rejected"},
])
def test_invalid_input(payload):
    assert client.post("/mock/inference", json=payload).status_code == 422


def test_disabled(monkeypatch):
    monkeypatch.delenv("INFERENCE_MOCK_ENABLED", raising=False)
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 503
    assert client.post("/mock/inference", json={"analysis_id": ANALYSIS_ID}).status_code == 404
