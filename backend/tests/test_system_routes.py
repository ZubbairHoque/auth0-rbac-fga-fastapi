import tracemalloc

from app.routes.system_routes import get_authz_service
from app.database import get_db, InvitationDB
from unittest.mock import AsyncMock, MagicMock
import pytest
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

tracemalloc.start()

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
    mock_authz.check_permission.return_value = False  # Not an admin
    
    app.dependency_overrides[get_authz_service] = lambda: mock_authz

    try:
        payload = {"user_id": "alice", "role": "admin"}
        response = client.post("/system/users?admin_user_id=notadmin", json=payload)
        
        assert response.status_code == 403
        assert response.json()["detail"] == "Only admins can manage users"
    finally:
        app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_invite_user_success():
    mock_authz = AsyncMock()
    mock_db = AsyncMock()

    mock_db.add = MagicMock()
    
    # Mock Admin check
    mock_authz.check_permission.return_value = True
        
    app.dependency_overrides[get_authz_service] = lambda: mock_authz
    app.dependency_overrides[get_db] = lambda: mock_db
    
    try:
        payload = {"email": "test@example.com", "role": "admin"}
        # Corrected endpoint: /system/invite
        response = client.post("/system/invite?admin_user_id=boss", json=payload)
        
        assert response.status_code == 200
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    finally:
        app.dependency_overrides = {}

@pytest.mark.asyncio 
async def test_invite_user_forbidden():
    mock_authz = AsyncMock()
    mock_db = AsyncMock()

    mock_db.add = MagicMock()

    mock_authz.check_permission.return_value = False  # Not an admin
    
    app.dependency_overrides[get_authz_service] = lambda: mock_authz
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        payload = {"email": "test@example.com", "role": "admin"}
        response = client.post(
            "/system/invite?admin_user_id=notadmin", json=payload
            )

        assert response.status_code == 403
        assert response.json()["detail"] == "Only admins can send invitations"

        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()
    finally:
        app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_webhook_sync_success():
    mock_authz = AsyncMock()
    mock_db = AsyncMock()
    
    # 1. Mock the DB query finding an invitation
    mock_invitation = MagicMock(spec=InvitationDB)
    mock_invitation.email = "test@example.com"
    mock_invitation.role = "admin"
    mock_invitation.is_used = False
    
    # Mock the DB execute result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_invitation
    mock_db.execute.return_value = mock_result
    
    # 2. Mock FGA success
    mock_authz.assign_user_role.return_value = True
        
    app.dependency_overrides[get_authz_service] = lambda: mock_authz
    app.dependency_overrides[get_db] = lambda: mock_db
    
    try:
        payload = {"email": "test@example.com", "user_id": "auth0|123"}
        response = client.post(
            "/system/auth/webhook/post-registration", json=payload
            )
        
        assert response.status_code == 200
        assert "synced to FGA" in response.json()["message"]
        
        # 3. Verify the state changes
        assert mock_invitation.is_used is True
        mock_authz.assign_user_role.assert_called_with("auth0|123", "admin")
        mock_db.commit.assert_called_once()
    finally:
        app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_webhook_sync_no_invitation():
    mock_authz = AsyncMock()
    mock_db = AsyncMock()
    
    # Mock the DB query returning no invitation
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
        
    app.dependency_overrides[get_authz_service] = lambda: mock_authz
    app.dependency_overrides[get_db] = lambda: mock_db
    
    try:
        payload = {"email": "test@example.com", "user_id": "auth0|123"}
        response = client.post(
            "/system/auth/webhook/post-registration", json=payload
            )

        assert response.status_code == 404
        assert response.json()["detail"] == "No invitation found for this email"

    finally:
        app.dependency_overrides = {}
