import tracemalloc
from app.routes.system_routes import get_authz_service, validate_webhook_signature
from app.database import get_db, InvitationDB
from unittest.mock import AsyncMock, MagicMock
import pytest
from app.main import app

tracemalloc.start()

@pytest.mark.asyncio
async def test_assign_role_success(client):
    mock_authz = AsyncMock()
    mock_authz.check_permission.return_value = True
    mock_authz.assign_user_role.return_value = True
    
    app.dependency_overrides[get_authz_service] = lambda: mock_authz

    try:
        payload = {"user_id": "alice", "role": "admin"}
        response = await client.post(
            "/system/users?admin_user_id=boss", json=payload
            )
        
        assert response.status_code == 200
        assert response.json()["message"] == "User alice assigned to admin"
    finally:
        app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_assign_role_forbidden(client):
    mock_authz = AsyncMock()
    mock_authz.check_permission.return_value = False
    
    app.dependency_overrides[get_authz_service] = lambda: mock_authz

    try:
        payload = {"user_id": "alice", "role": "admin"}
        response = await client.post(
            "/system/users?admin_user_id=notadmin", json=payload
            )
        
        assert response.status_code == 403
    finally:
        app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_invite_user_success(client):
    mock_authz = AsyncMock()
    mock_db = AsyncMock()

    mock_db.add = MagicMock() 
    mock_db.commit = AsyncMock()
    
    mock_authz.check_permission.return_value = True

    app.dependency_overrides[get_authz_service] = lambda: mock_authz
    app.dependency_overrides[get_db] = lambda: mock_db
    
    try:
        payload = {"email": "test@example.com", "role": "admin"}
        response = await client.post(
            "/system/invite?admin_user_id=boss", json=payload
            )
        
        assert response.status_code == 200
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    finally:
        app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_webhook_sync_success(client):
    mock_webhook_guard = AsyncMock()
    mock_authz = AsyncMock()
    mock_db = MagicMock()

    mock_db.commit = AsyncMock()
    mock_db.execute =  AsyncMock()
    
    # 1. Mock DB finding an invitation
    mock_invitation = MagicMock(spec=InvitationDB)
    mock_invitation.email = "test@example.com"
    mock_invitation.role = "admin"
    mock_invitation.is_used = False
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_invitation
    mock_db.execute.return_value = mock_result
    
    # 2. Mock FGA success
    mock_authz.assign_user_role.return_value = True

    # 3. Bypass the Bouncer
    app.dependency_overrides[validate_webhook_signature] = lambda: mock_webhook_guard    
    app.dependency_overrides[get_authz_service] = lambda: mock_authz
    app.dependency_overrides[get_db] = lambda: mock_db
    
    try:
        payload = {"email": "test@example.com", "user_id": "auth0|123"}
        response = await client.post(
            "/system/auth/webhook/post-registration", json=payload
            )
        
        assert response.status_code == 200
        assert "Successfully synced test@example.com to FGA" in response.json()[
            "message"
            ]
        
        assert mock_invitation.is_used is True
        mock_db.commit.assert_called_once()
    finally:
        app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_webhook_sync_no_invitation(client):
    mock_webhook_guard = AsyncMock() # Need the bouncer bypass!
    mock_authz = AsyncMock()
    mock_db = AsyncMock()
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
        
    app.dependency_overrides[validate_webhook_signature] = lambda: mock_webhook_guard
    app.dependency_overrides[get_authz_service] = lambda: mock_authz
    app.dependency_overrides[get_db] = lambda: mock_db
    
    try:
        payload = {"email": "stranger@example.com", "user_id": "auth0|123"}
        response = await client.post(
            "/system/auth/webhook/post-registration", json=payload
            )

        # Should be 404 (Not Found), not 401 (Unauthorized)
        assert response.status_code == 404
        assert response.json()["detail"] == "No pending invitation found"
    finally:
        app.dependency_overrides = {}
