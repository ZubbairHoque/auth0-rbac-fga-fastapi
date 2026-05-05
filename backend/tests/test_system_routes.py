from app.routes.system_routes import get_authz_service
from unittest.mock import AsyncMock
import pytest
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

@pytest.mark.asyncio
async def test_assign_role_success():
    mock_authz = AsyncMock()
    mock_authz.check_permission.return_value = True
    mock_authz.assign_user_role.return_value = True
    
    app.dependency_overrides[get_authz_service] = lambda: mock_authz

    try:
        payload = {"user_id": "alice", "role": "admin"}
        response = client.post("/system/users?admin_user_id=boss", json=payload)
        
        assert response.status_code == 200
        assert response.json()["message"] == "User alice assigned to admin"
    finally:
        app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_assign_role_forbidden():
    mock_authz = AsyncMock()
    mock_authz.check_permission.return_value = False # Not an admin!
    
    app.dependency_overrides[get_authz_service] = lambda: mock_authz

    try:
        payload = {"user_id": "alice", "role": "admin"}
        response = client.post("/system/users?admin_user_id=hacker", json=payload)
        
        assert response.status_code == 403
        assert response.json()["detail"] == "Only admins can manage users"
    finally:
        app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_remove_role_success():
    mock_authz = AsyncMock()
    mock_authz.check_permission.return_value = True
    mock_authz.remove_user_role.return_value = True
    
    app.dependency_overrides[get_authz_service] = lambda: mock_authz

    try:
        response = client.delete("/system/users/alice?role=admin&admin_user_id=boss")
        
        assert response.status_code == 200
        assert response.json()["message"] == "User alice removed from admin"
    finally:
        app.dependency_overrides = {}
