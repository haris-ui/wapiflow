import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check_root(client: AsyncClient):
    """Verify /health returns 200 with ok status and version."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert data["version"] == "1.0.0"
    assert "environment" in data
    assert "X-Request-ID" in response.headers


@pytest.mark.asyncio
async def test_health_check_v1_prefix(client: AsyncClient):
    """Verify /api/v1/health returns 200 with ok status."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert data["version"] == "1.0.0"
