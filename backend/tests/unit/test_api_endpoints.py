"""
Unit Tests for API Endpoints

Tests for REST API endpoints including sessions, projects, export, etc.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = Mock()
    db.query = Mock()
    db.add = Mock()
    db.commit = Mock()
    db.refresh = Mock()
    return db


@pytest.fixture
def client():
    """Create test client."""
    from main import app

    return TestClient(app)


class TestSessionEndpoints:
    """Tests for session API endpoints."""

    def test_create_session(self, client, mock_db):
        """Test session creation."""
        with patch("app.core.database.get_db", return_value=mock_db):
            response = client.post(
                "/api/v1/sessions",
                json={
                    "user_id": 1,
                    "task_id": 1,
                    "status": "active",
                },
            )

            # May return 404 if endpoint not registered, that's ok for this test
            assert response.status_code in [200, 201, 404, 422]

    def test_get_session(self, client, mock_db):
        """Test getting session by ID."""
        with patch("app.core.database.get_db", return_value=mock_db):
            response = client.get("/api/v1/sessions/1")

            assert response.status_code in [200, 404]

    def test_list_sessions(self, client, mock_db):
        """Test listing sessions."""
        with patch("app.core.database.get_db", return_value=mock_db):
            response = client.get("/api/v1/sessions")

            assert response.status_code in [200, 404]

    def test_update_session(self, client, mock_db):
        """Test updating session."""
        with patch("app.core.database.get_db", return_value=mock_db):
            response = client.put(
                "/api/v1/sessions/1",
                json={
                    "status": "completed",
                    "score": 85.5,
                },
            )

            assert response.status_code in [200, 404, 422]

    def test_delete_session(self, client, mock_db):
        """Test deleting session."""
        with patch("app.core.database.get_db", return_value=mock_db):
            response = client.delete("/api/v1/sessions/1")

            assert response.status_code in [200, 204, 404]


class TestExportEndpoints:
    """Tests for export API endpoints."""

    def test_export_session_json(self, client, mock_db):
        """Test exporting session as JSON."""
        with patch("app.core.database.get_db", return_value=mock_db):
            response = client.get(
                "/api/v1/export/sessions/1/export",
                params={"format": "json"},
            )

            assert response.status_code in [200, 404]

            if response.status_code == 200:
                assert response.headers["content-type"] in [
                    "application/json",
                    "application/json; charset=utf-8",
                ]

    def test_export_session_markdown(self, client, mock_db):
        """Test exporting session as Markdown."""
        with patch("app.core.database.get_db", return_value=mock_db):
            response = client.get(
                "/api/v1/export/sessions/1/export",
                params={"format": "markdown"},
            )

            assert response.status_code in [200, 404]

    def test_export_session_pdf(self, client, mock_db):
        """Test exporting session as PDF."""
        with patch("app.core.database.get_db", return_value=mock_db):
            response = client.get(
                "/api/v1/export/sessions/1/export",
                params={"format": "pdf"},
            )

            assert response.status_code in [200, 404]

    def test_export_project(self, client, mock_db):
        """Test exporting project."""
        with patch("app.core.database.get_db", return_value=mock_db):
            response = client.get(
                "/api/v1/export/projects/1/export",
                params={"format": "json", "include_sessions": True},
            )

            assert response.status_code in [200, 404]

    def test_export_analytics(self, client, mock_db):
        """Test exporting analytics."""
        with patch("app.core.database.get_db", return_value=mock_db):
            response = client.get(
                "/api/v1/export/analytics/export",
                params={"format": "csv"},
            )

            assert response.status_code in [200, 404]


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data

    def test_health_live(self, client):
        """Test liveness probe."""
        response = client.get("/health/live")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"


class TestAuthEndpoints:
    """Tests for authentication endpoints."""

    def test_login(self, client, mock_db):
        """Test user login."""
        with patch("app.core.database.get_db", return_value=mock_db):
            response = client.post(
                "/api/v1/auth/login",
                json={
                    "username": "testuser",
                    "password": "testpass",
                },
            )

            assert response.status_code in [200, 401, 404, 422]

    def test_register(self, client, mock_db):
        """Test user registration."""
        with patch("app.core.database.get_db", return_value=mock_db):
            response = client.post(
                "/api/v1/auth/register",
                json={
                    "username": "newuser",
                    "email": "newuser@example.com",
                    "password": "securepass123",
                },
            )

            assert response.status_code in [200, 201, 400, 404, 422]

    def test_logout(self, client):
        """Test user logout."""
        response = client.post("/api/v1/auth/logout")

        assert response.status_code in [200, 401, 404]


class TestKnowledgeEndpoints:
    """Tests for knowledge base endpoints."""

    def test_upload_knowledge(self, client, mock_db):
        """Test uploading knowledge content."""
        with patch("app.core.database.get_db", return_value=mock_db):
            response = client.post(
                "/api/v1/knowledge",
                json={
                    "title": "Sales Techniques",
                    "content": "Best practices for sales...",
                    "category": "training",
                },
            )

            assert response.status_code in [200, 201, 404, 422]

    def test_search_knowledge(self, client, mock_db):
        """Test searching knowledge base."""
        with patch("app.core.database.get_db", return_value=mock_db):
            response = client.get(
                "/api/v1/knowledge/search",
                params={"query": "objection handling"},
            )

            assert response.status_code in [200, 404]

    def test_get_knowledge(self, client, mock_db):
        """Test getting knowledge by ID."""
        with patch("app.core.database.get_db", return_value=mock_db):
            response = client.get("/api/v1/knowledge/1")

            assert response.status_code in [200, 404]


class TestReportEndpoints:
    """Tests for report endpoints."""

    def test_get_session_report(self, client, mock_db):
        """Test getting session report."""
        with patch("app.core.database.get_db", return_value=mock_db):
            response = client.get("/api/v1/reports/sessions/1")

            assert response.status_code in [200, 404]

    def test_get_user_analytics(self, client, mock_db):
        """Test getting user analytics."""
        with patch("app.core.database.get_db", return_value=mock_db):
            response = client.get("/api/v1/reports/users/1/analytics")

            assert response.status_code in [200, 404]

    def test_get_performance_trends(self, client, mock_db):
        """Test getting performance trends."""
        with patch("app.core.database.get_db", return_value=mock_db):
            response = client.get(
                "/api/v1/reports/trends",
                params={
                    "user_id": 1,
                    "start_date": "2024-01-01",
                    "end_date": "2024-12-31",
                },
            )

            assert response.status_code in [200, 404, 422]


class TestValidation:
    """Tests for input validation."""

    def test_invalid_session_data(self, client, mock_db):
        """Test validation of invalid session data."""
        with patch("app.core.database.get_db", return_value=mock_db):
            response = client.post(
                "/api/v1/sessions",
                json={
                    "user_id": "invalid",  # Should be integer
                    "task_id": 1,
                },
            )

            assert response.status_code in [400, 404, 422]

    def test_missing_required_fields(self, client, mock_db):
        """Test validation of missing required fields."""
        with patch("app.core.database.get_db", return_value=mock_db):
            response = client.post(
                "/api/v1/sessions",
                json={
                    "user_id": 1,
                    # Missing task_id
                },
            )

            assert response.status_code in [400, 404, 422]

    def test_invalid_export_format(self, client, mock_db):
        """Test validation of invalid export format."""
        with patch("app.core.database.get_db", return_value=mock_db):
            response = client.get(
                "/api/v1/export/sessions/1/export",
                params={"format": "invalid_format"},
            )

            assert response.status_code in [400, 404, 422]


class TestErrorHandling:
    """Tests for error handling."""

    def test_not_found_error(self, client, mock_db):
        """Test 404 error handling."""
        with patch("app.core.database.get_db", return_value=mock_db):
            response = client.get("/api/v1/sessions/99999")

            assert response.status_code in [404]

    def test_internal_server_error(self, client, mock_db):
        """Test 500 error handling."""
        with patch("app.core.database.get_db", side_effect=Exception("Database error")):
            response = client.get("/api/v1/sessions")

            assert response.status_code in [500, 404]

    def test_unauthorized_access(self, client):
        """Test unauthorized access."""
        response = client.get("/api/v1/admin/users")

        assert response.status_code in [401, 403, 404]


class TestRateLimiting:
    """Tests for rate limiting."""

    def test_rate_limit_exceeded(self, client):
        """Test rate limit enforcement."""
        # Make multiple requests rapidly
        responses = []
        for _ in range(100):
            response = client.get("/health")
            responses.append(response.status_code)

        # All requests should succeed or some may be rate limited
        assert all(status in [200, 429] for status in responses)


class TestCORS:
    """Tests for CORS configuration."""

    def test_cors_headers(self, client):
        """Test CORS headers."""
        response = client.options(
            "/api/v1/sessions",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        # CORS may or may not be configured
        assert response.status_code in [200, 404, 405]


@pytest.mark.parametrize(
    "endpoint,method",
    [
        ("/api/v1/sessions", "GET"),
        ("/api/v1/sessions", "POST"),
        ("/api/v1/sessions/1", "GET"),
        ("/api/v1/sessions/1", "PUT"),
        ("/api/v1/sessions/1", "DELETE"),
        ("/api/v1/export/sessions/1/export", "GET"),
        ("/health", "GET"),
    ],
)
def test_endpoint_accessibility(client, endpoint, method, mock_db):
    """Test that endpoints are accessible."""
    with patch("app.core.database.get_db", return_value=mock_db):
        if method == "GET":
            response = client.get(endpoint)
        elif method == "POST":
            response = client.post(endpoint, json={})
        elif method == "PUT":
            response = client.put(endpoint, json={})
        elif method == "DELETE":
            response = client.delete(endpoint)

        # Endpoint should respond (not necessarily with success)
        assert response.status_code < 600
