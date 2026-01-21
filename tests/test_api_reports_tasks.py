import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_get_task_stats(async_client: AsyncClient):
    response = await async_client.get("/api/v1/reports/stats/tasks")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "completed" in data
    assert "inProgress" in data
    assert "notStarted" in data
    assert "averageScore" in data
    assert isinstance(data["total"], int)

@pytest.mark.asyncio
async def test_get_tasks_list(async_client: AsyncClient):
    # Test getting all tasks
    response = await async_client.get("/api/v1/reports/tasks?status=all")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    
    # Test getting completed tasks (might be empty but should work)
    response = await async_client.get("/api/v1/reports/tasks?status=completed")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_get_tasks_structure(async_client: AsyncClient):
    # Assuming the DB might be empty or seeded, we just check if it doesn't crash
    # If we have data, we check structure
    response = await async_client.get("/api/v1/reports/tasks")
    data = response.json()
    
    if len(data) > 0:
        task = data[0]
        assert "id" in task
        assert "courseName" in task
        assert "courseTags" in task
        assert "status" in task
        assert "progress" in task
        assert "completed" in task["progress"]
        assert "total" in task["progress"]
