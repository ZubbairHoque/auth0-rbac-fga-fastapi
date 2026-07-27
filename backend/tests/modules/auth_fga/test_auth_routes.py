import tracemalloc
from unittest.mock import AsyncMock, Mock
from fastapi.testclient import TestClient
from fastapi.exceptions import HTTPException
import pytest
from app.main import app
from app.modules.auth_fga.routes import get_authz_service
from app.core.security import verify_signature
from app.modules.auth_fga.routes import validate_webhook_signature


tracemalloc.start()

client = TestClient(app)

@pytest.mark.asyncio
async def test_validate_webhook_signature_success(monkeypatch):
    mock_request = AsyncMock()
    mock_request.body.return_value = b"raw body"
    mock_verify_signature = Mock(return_value=True)
    monkeypatch.setattr(
        "app.modules.auth_fga.routes.verify_signature", 
        mock_verify_signature
    )
        
    result = await validate_webhook_signature(mock_request, x_auth0_signature="fake")
    assert result is None
    mock_verify_signature.assert_called_once()

@pytest.mark.asyncio
async def test_validate_webhook_web_signature_not_found():
    """Test that the signature is required, by removing x_auth0_signature."""

    mock_request = AsyncMock()
 
    # no x_auth0_signature header
    with pytest.raises(HTTPException) as exc_info:
        await validate_webhook_signature(mock_request, x_auth0_signature=None)


    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Webhook signature missing"

@pytest.mark.asyncio
async def test_validate_webhook_signature_fail():
    mock_request = AsyncMock()
    mock_request.body.return_value = b"raw body"
    mock_verify_signature = AsyncMock(return_value=False)
    
    app.dependency_overrides[verify_signature] = lambda x, y, z: mock_verify_signature
    
    with pytest.raises(HTTPException) as exc_info:
        await validate_webhook_signature(mock_request)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Invalid webhook signature"

@pytest.mark.asyncio
async def test_get_health(monkeypatch):

    monkeypatch.setattr(
        "app.modules.auth_fga.routes.authz_service.check_auth0_fga_health",
        AsyncMock(return_value=True)
    )
    response = client.get("/auth/health")
    assert response.status_code == 200
    assert response.json() ==  {
        "status": "ok", "message": "Auth0 FGA connection is healthy"
    }

@pytest.mark.asyncio
async def test_dashboard_access_success():
    mock_service = AsyncMock()
    mock_service.validate_dashboard_access.return_value = True

    app.dependency_overrides[get_authz_service] = lambda: mock_service
    response = client.get("/auth/validate/admin", params={"user_id": "user123"})
    assert response.status_code == 200
    assert response.json() ==  {"authorized":True}

@pytest.mark.asyncio
async def test_dashboard_access_fail():
    mock_service = AsyncMock()
    mock_service.validate_dashboard_access.return_value = False

    app.dependency_overrides[get_authz_service] = lambda: mock_service
    response = client.get("/auth/validate/admin", params={"user_id": "user123"})
    assert response.status_code == 403
    assert response.json() ==  {"detail":"Access denied to admin dashboard."}

@pytest.mark.asyncio
async def test_assign_role_success(client):
    mock_authz = AsyncMock()
    mock_authz.check_permission.return_value = True
    mock_authz.assign_user_role.return_value = True
    
    app.dependency_overrides[get_authz_service] = lambda: mock_authz

    try:
        payload = {"user_id": "alice", "role": "admin"}
        response = await client.post(
            "/auth/users?admin_user_id=boss", json=payload
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
            "/auth/users?admin_user_id=notadmin", json=payload
            )
        
        assert response.status_code == 403
    finally:
        app.dependency_overrides = {}


