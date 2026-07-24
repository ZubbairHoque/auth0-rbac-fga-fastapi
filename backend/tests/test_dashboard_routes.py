from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
import pytest
from app.main import app
from app.modules.auth_fga.routes import get_authz_service

client = TestClient(app)

@pytest.mark.asyncio
async def test_dashboard_routes():
    mock_service = AsyncMock()
    mock_service.validate_dashboard_access.return_value = True

    app.dependency_overrides[get_authz_service] = lambda: mock_service
    response = client.get("/auth/validate/admin", params={"user_id": "user123"})
    assert response.status_code == 200
    assert response.json() ==  {"authorized":True}

