from unittest.mock import AsyncMock
import pytest
from fastapi.testclient import TestClient
from app.main import app, lifespan
from app.routes.resource_routes import get_authz_service

client = TestClient(app)

@pytest.mark.asyncio
async def test_lifespan():
    mock_authz = AsyncMock()
    mock_authz.check_auth0_fga_health.return_value = True
    app.dependency_overrides[get_authz_service] = lambda: mock_authz

@pytest.mark.asyncio
async def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "message": "Welcome to your Single-Tenant Internal App",
        "docs": "/docs"
    }

@pytest.mark.asyncio
async def test_docs():
    response = client.get("/docs")
    assert response.status_code == 200

