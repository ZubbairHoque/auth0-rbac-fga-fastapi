from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi.testclient import TestClient
from app.database import ResourceDB, get_db
from app.main import app
from app.routes.resource_routes import get_authz_service

client = TestClient(app)

@pytest.mark.asyncio
async def test_get_resource_forbidden():
    # 1. Arrange - Mock Auth Service to deny access
    mock_authz = AsyncMock()
    mock_authz.check_permission.return_value = False
    
    # Mock DB just in case, though it shouldn't be reached
    mock_db = AsyncMock()
    app.dependency_overrides[get_authz_service] = lambda: mock_authz
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        # 2. Act
        response = client.get("/resources/res1?user_id=hacker")
        
        # 3. Assert
        assert response.status_code == 403
        assert response.json()["detail"] == "Access denied"
    finally:
        app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_create_resource_success():
    # 1. Arrange Mocks
    mock_db = AsyncMock()
    mock_db.add = MagicMock()

    mock_authz = AsyncMock()
    mock_authz.check_permission.return_value = True

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_authz_service] = lambda: mock_authz

    try:
        # 2. Act
        payload = {"name": "Test", "description": "...", "resource_type": "api"}
        response = client.post("/resources/?user_id=admin", json=payload)

        # 3. Assert
        assert response.status_code == 200
        
        mock_db.add.assert_called_once()
        # Verify the object passed to db.add has the correct attributes
        added_resource = mock_db.add.call_args[0][0]
        assert added_resource.name == "Test"
        assert added_resource.description == "..."
        assert added_resource.resource_type == "api"

        mock_authz.link_resource_to_system.assert_called_once()
    finally:
        app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_list_resource():
    # 1. Arrange - Mock Database
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [
        ResourceDB(id="res1", name="Resource 1", resource_type="api")
    ]
    mock_db.execute.return_value = mock_result

    # 2. Arrange - Mock Auth Service
    mock_authz = AsyncMock()
    mock_authz.get_user_resources.return_value = ["res1"]

    # 3. Apply Overrides
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_authz_service] = lambda: mock_authz

    try:
        # 4. Act
        response = client.get("/resources/?user_id=user123")
        
        # 5. Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "res1"
    finally:
        # Always cleanup
        app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_get_resource_success():
    # 1. Arrange
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = ResourceDB(id="res1", name="Resource 1", resource_type="api")
    mock_db.execute.return_value = mock_result

    mock_authz = AsyncMock()
    mock_authz.check_permission.return_value = True

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_authz_service] = lambda: mock_authz

    try:
        # 2. Act
        response = client.get("/resources/res1?user_id=user123")

        # 3. Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "res1"
    finally:
        app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_get_resource_not_found():
    # 1. Arrange
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    mock_authz = AsyncMock()
    mock_authz.check_permission.return_value = True

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_authz_service] = lambda: mock_authz

    try:
        # 2. Act
        response = client.get("/resources/res1?user_id=user123")

        # 3. Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Resource not found"
    finally:
        app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_delete_resource_success():
    # 1. Arrange
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = ResourceDB(id="res1", name="Resource 1", resource_type="api")
    mock_db.execute.return_value = mock_result

    mock_authz = AsyncMock()
    mock_authz.check_permission.return_value = True

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_authz_service] = lambda: mock_authz

    try:
        # 2. Act
        response = client.delete("/resources/res1?user_id=user123")

        # 3. Assert
        assert response.status_code == 200
        assert response.json()["message"] == "Resource deleted successfully"
        mock_db.delete.assert_called_once()
    finally:
        app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_delete_resource_not_found():
    # 1. Arrange
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    mock_authz = AsyncMock()
    mock_authz.check_permission.return_value = True

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_authz_service] = lambda: mock_authz

    try:
        # 2. Act
        response = client.delete("/resources/res1?user_id=user123")

        # 3. Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Resource not found"
    finally:
        app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_delete_resource_forbidden():
    # 1. Arrange
    mock_authz = AsyncMock()
    mock_authz.check_permission.return_value = False

    app.dependency_overrides[get_authz_service] = lambda: mock_authz

    try:
        # 2. Act
        response = client.delete("/resources/res1?user_id=user123")

        # 3. Assert
        assert response.status_code == 403
        assert response.json()["detail"] == "Admin access required"
    finally:
        app.dependency_overrides = {}