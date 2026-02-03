import pytest
from httpx import AsyncClient, ASGITransport
from main import app


@pytest.mark.asyncio
async def test_explainability_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/profile/test_user/why-not-improved")
        assert resp.status_code == 200
        data = resp.json()
        assert "diagnosis" in data
        assert "evidence" in data

        resp = await ac.get("/api/v1/profile/test_user/why-this-curriculum")
        assert resp.status_code == 200
        data = resp.json()
        if "reasoning" in data:
            assert True
        else:
            assert "recommended_focus" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
