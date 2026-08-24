"""API tests require neither GPU nor model bundle."""
from fastapi.testclient import TestClient
from src.api.main import app
client=TestClient(app)
def test_health(): assert client.get("/health").json()["status"] == "ok"
def test_unconfigured_ready(monkeypatch):
    monkeypatch.delenv("MODEL_BUNDLE_URI",raising=False); assert client.get("/ready").json()["status"] == "MODEL_NOT_CONFIGURED"
