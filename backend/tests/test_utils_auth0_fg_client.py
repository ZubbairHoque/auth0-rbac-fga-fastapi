import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.modules.auth_fga.client import Auth0FGAClient

@pytest.mark.asyncio
async def test_get_client_lazy_init():
    wrapper = Auth0FGAClient()
    assert wrapper._client is None
    
    with patch("app.utils.auth0_fga_client.OpenFgaClient") as mock_sdk_class:
        # First call: Should initialize
        _ = wrapper._get_client()
        mock_sdk_class.assert_called_once()
        assert wrapper._client is not None

        # Second call: Should NOT re-initialize
        _ = wrapper._get_client()
        assert mock_sdk_class.call_count == 1

@pytest.mark.asyncio
async def test_check_permission():
    wrapper = Auth0FGAClient()
    mock_sdk = MagicMock()
    mock_sdk.check = AsyncMock()
    mock_sdk.check.return_value.allowed = True
    wrapper._client = mock_sdk

    result = await wrapper.check_permission("user:alice", "view", "doc:1")

    assert result is True
    mock_sdk.check.assert_called_once()
    
    # Verify inner request data
    args = mock_sdk.check.call_args[0][0]
    assert args.user == "user:alice"
    assert args.relation == "view"
    assert args.object == "doc:1"

@pytest.mark.asyncio
async def test_write_tuples():
    wrapper = Auth0FGAClient()
    mock_sdk = MagicMock()
    mock_sdk.write = AsyncMock()
    wrapper._client = mock_sdk

    dummy_tuples = [MagicMock()]
    result = await wrapper.write_tuples(dummy_tuples)
    
    assert result is True
    mock_sdk.write.assert_called_once()

@pytest.mark.asyncio
async def test_delete_tuples():
    wrapper = Auth0FGAClient()
    mock_sdk = MagicMock()
    mock_sdk.write = AsyncMock() # Delete uses the same .write() method in FGA SDK
    wrapper._client = mock_sdk

    dummy_tuples = [MagicMock()]
    result = await wrapper.delete_tuples(dummy_tuples)
    
    assert result is True
    mock_sdk.write.assert_called_once()

@pytest.mark.asyncio
async def test_list_objects():
    wrapper = Auth0FGAClient()
    mock_sdk = MagicMock()
    mock_sdk.list_objects = AsyncMock()
    # FGA list_objects returns an object with an 'objects' attribute
    mock_sdk.list_objects.return_value.objects = ["res:1", "res:2"]
    wrapper._client = mock_sdk

    results = await wrapper.list_objects("user:alice", "view", "resource")
    
    assert results == ["res:1", "res:2"]
    mock_sdk.list_objects.assert_called_once()

@pytest.mark.asyncio
async def test_health_check():
    wrapper = Auth0FGAClient()
    mock_sdk = MagicMock()
    mock_sdk.read_authorization_models = AsyncMock()
    wrapper._client = mock_sdk

    result = await wrapper.health_check()
    
    assert result is True
    mock_sdk.read_authorization_models.assert_called_once()
