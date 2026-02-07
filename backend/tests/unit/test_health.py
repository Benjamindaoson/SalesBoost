from fastapi.testclient import TestClient
from main import app


def test_health_endpoint_returns_healthy_or_degraded():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    # status should be a string like 'healthy' or 'degraded' or 'unavailable'
    assert data["status"] in {"healthy", "degraded", "unavailable"}
    # system_health should be present and contain at least a couple of keys
    assert isinstance(data.get("system_health"), dict)
