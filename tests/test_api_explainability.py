import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_explainability_endpoints():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # We assume user "test_user" exists or returns 404/empty.
        # Actually, the endpoints default to empty stats if no data.
        
        # 1. Why Not Improved
        resp = await ac.get("/api/v1/profile/test_user/why-not-improved")
        assert resp.status_code == 200
        data = resp.json()
        assert "diagnosis" in data
        assert "evidence" in data
        
        # 2. Why This Curriculum
        resp = await ac.get("/api/v1/profile/test_user/why-this-curriculum")
        assert resp.status_code == 200
        data = resp.json()
        # If no profile, it returns maintenance mode
        if "reasoning" in data:
            assert True
        else:
            assert "recommended_focus" in data

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
