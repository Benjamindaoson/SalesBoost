from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    data = response.json()
    assert response.status_code == 200
    assert data["status"] == "healthy"
