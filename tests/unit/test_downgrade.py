from fastapi.testclient import TestClient
from main import app

from app.downgrade_manager import downgrade_manager


def test_downgrade_mechanism_initially_no_issues():
    # Ensure there are no active downgrades at startup
    downgrade_manager.clear()
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    system = data.get("system_health", {})
    assert isinstance(system, dict)
    assert isinstance(system.get("downgrades"), list)
    assert len(system["downgrades"]) == 0


def test_downgrade_status_triggers_and_exposes():
    client = TestClient(app)
    # Trigger a downgrade by manually registering an issue
    downgrade_manager.register("db", "simulated failure for testing")
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    system = data.get("system_health", {})
    downgrades = system.get("downgrades", [])
    assert any(item.startswith("db:") for item in downgrades)
    # Clean up for subsequent tests
    downgrade_manager.clear()
