import uuid

import pytest
from fastapi.testclient import TestClient

from api.auth_schemas import UserSchema
from api.deps import audit_access, require_user
from core.config import EnvironmentState, settings
from main import app
from schemas.memory_service import AuditTraceResponse, MemoryQueryResponse


def _override_user():
    return UserSchema(id="u1", username="tester", role="admin", tenant_id="t1")


async def _override_audit_access():
    return None


@pytest.fixture(scope="module")
def client():
    settings.ENV_STATE = EnvironmentState.DEVELOPMENT
    app.dependency_overrides[require_user] = _override_user
    app.dependency_overrides[audit_access] = _override_audit_access
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides = {}


def test_memory_query_response_schema(client):
    request_id = f"req-{uuid.uuid4()}"
    payload = {
        "query": "年费怎么减免？",
        "tenant_id": "t1",
        "user_id": "u1",
        "session_id": "s1",
        "intent_hint": "权益问答",
        "stage": "需求确认",
        "objection_type": None,
        "top_k": 3,
        "require_citations": True,
        "route_policy": "compliance>knowledge>strategy>fallback",
    }
    resp = client.post(
        "/api/v1/memory/query",
        json=payload,
        headers={"x-request-id": request_id, "x-tenant-id": "t1"},
    )
    assert resp.status_code == 200
    data = resp.json()
    parsed = MemoryQueryResponse.parse_obj(data)
    assert parsed.request_id == request_id
    assert parsed.data.route_decision in {"knowledge", "strategy", "fallback", "compliance"}


def test_memory_trace_response_schema(client):
    request_id = f"req-{uuid.uuid4()}"
    query_payload = {
        "query": "年费怎么减免？",
        "tenant_id": "t1",
        "user_id": "u1",
        "session_id": "s1",
        "intent_hint": "权益问答",
        "stage": "需求确认",
        "objection_type": None,
        "top_k": 3,
        "require_citations": True,
        "route_policy": "compliance>knowledge>strategy>fallback",
    }
    resp = client.post(
        "/api/v1/memory/query",
        json=query_payload,
        headers={"x-request-id": request_id, "x-tenant-id": "t1"},
    )
    assert resp.status_code == 200

    trace_resp = client.post(
        "/api/v1/memory/trace",
        json={"request_id": request_id},
        headers={"x-request-id": request_id, "x-tenant-id": "t1"},
    )
    assert trace_resp.status_code == 200
    trace_data = AuditTraceResponse.parse_obj(trace_resp.json())
    assert trace_data.request_id == request_id
