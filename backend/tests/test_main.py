from unittest.mock import AsyncMock
from httpx import ASGITransport, AsyncClient
import pytest
from app.main import app
from app.modules.resource.routes import get_authz_service
from app.core.database import get_db

@pytest.mark.asyncio
async def test_lifespan():
    mock_authz = AsyncMock()
    mock_authz.check_auth0_fga_health.return_value = True
    app.dependency_overrides[get_authz_service] = lambda: mock_authz

@pytest.mark.anyio
async def test_root_async():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:

        response = await ac.get("/")

    assert response.status_code == 200

@pytest.mark.asyncio
async def test_root(client):
    response = await client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "message": "Welcome to your Single-Tenant Internal App",
        "docs": "/docs"
    }

@pytest.mark.asyncio
async def test_read_items(db_session):
    """Test if we can read Resources table"""
    from app.modules.resource.model import ResourceDB

    new_item = ResourceDB(id="124", name="Test Item", resource_type="sensor")

    db_session.add(new_item)
    await db_session.commit()

    app.dependency_overrides[get_db] = lambda: db_session

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/items")

    assert response.status_code == 200
    data = response.json()
    assert data[0]["name"] == "Test Item"

    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_docs(client):

    response = await client.get("/docs")
    assert response.status_code == 200

