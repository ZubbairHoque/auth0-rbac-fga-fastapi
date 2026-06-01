import pytest
from unittest.mock import AsyncMock, patch

import pytest_asyncio
from app.services.authorization_service import authz_service


@pytest.fixture
def mock_fga():
    with patch('app.services.authorization_service.fga_client') as mock:
        mock.write_tuples = AsyncMock(return_value=True)
        mock.delete_tuples = AsyncMock(return_value=True)
        mock.check_permission = AsyncMock(return_value=True)
        mock.list_objects = AsyncMock(return_value=["resource:1", "resource:2"])
        mock.health_check = AsyncMock(return_value=True)
        yield mock

@pytest.mark.asyncio
async def test_assign_user_role(mock_fga):
    result = await authz_service.assign_user_role("user123", "admin")
    
    assert result is True
    mock_fga.write_tuples.assert_called_once()
    
    # Test invalid role
    with pytest.raises(ValueError, match="Role must be in"):
        await authz_service.assign_user_role("user123", "superadmin")

@pytest.mark.asyncio
async def test_remove_user_role(mock_fga):
    result = await authz_service.remove_user_role("user123", "admin")
    
    assert result is True
    mock_fga.delete_tuples.assert_called_once()
    
    # Test invalid role
    with pytest.raises(ValueError, match="Role must be in"):
        await authz_service.remove_user_role("user123", "superadmin")

@pytest.mark.asyncio
async def test_link_resource_to_system(mock_fga):
    result = await authz_service.link_resource_to_system("res-456")
    
    assert result is True
    mock_fga.write_tuples.assert_called_once()

@pytest.mark.asyncio
async def test_check_permission(mock_fga):
    # Check resource permission
    result = await authz_service.check_permission("user123", "can_view", "res-456")
    
    assert result is True
    mock_fga.check_permission.assert_called_once_with(
        user="user:user123",
        relation="can_view",
        object_id="resource:res-456"
    )
    
    mock_fga.check_permission.reset_mock()
    
    # Check system permission
    result = await authz_service.check_permission("user123", "can_create_resource")
    
    assert result is True
    mock_fga.check_permission.assert_called_once_with(
        user="user:user123",
        relation="can_create_resource",
        object_id="system:main"
    )

@pytest.mark.asyncio
async def test_validate_dashboard_access(mock_fga):
    result = await authz_service.validate_dashboard_access("user123", "admin")
    
    assert result is True
    mock_fga.check_permission.assert_called_once_with(
        user="user:user123",
        relation="can_access_admin_dashboard",
        object_id="system:main"
    )

@pytest.mark.asyncio
async def test_get_user_resources(mock_fga):
    results = await authz_service.get_user_resources("user123")
    
    assert results == ["1", "2"]
    mock_fga.list_objects.assert_called_once_with(
        user="user:user123",
        relation="can_view",
        object_type="resource"
    )

@pytest.mark.asyncio
async def test_check_auth0_fga_health(mock_fga):
    result = await authz_service.check_auth0_fga_health()
    
    assert result is True
    mock_fga.health_check.assert_called_once()