from fastapi.testclient import TestClient
import pytest

from main import app


@pytest.mark.asyncio
def test_input_validation_disallowed_content_type():
    client = TestClient(app)
    resp = client.post(
        "/api/v1/auth/token",
        data="username=user&password=pass",
        headers={"Content-Type": "application/xml"},
    )
    assert resp.status_code == 415


def test_input_validation_large_body():
    client = TestClient(app)
    large = "A" * 1_100_000  # > 1MB
    resp = client.post(
        "/api/v1/auth/token",
        data=large,
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 413
