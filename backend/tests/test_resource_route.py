import json
from unittest.mock import AsyncMock, MagicMock
import pytest
from sqlalchemy import select
from app.database import ResourceDB, get_db
from app.main import app
from app.routes.resource_routes import get_authz_service, get_current_user

# Fixture to create a client for our async backend

@pytest.mark.asyncio
async def test_get_resource_sucess(db_session, client):

    # 1. ARRANGE: Put data in so the GET can find it
    resource = ResourceDB(
            id="res1", 
            name="Integration Test Resource", 
            description="...",
            resource_type="api"
        )
        
    db_session.add(resource)
    await db_session.commit()

    mock_authz = AsyncMock()
    mock_authz.check_permission.return_value = True
    
    app.dependency_overrides[get_current_user] = lambda: "user123"
    app.dependency_overrides[get_authz_service] = lambda: mock_authz
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        # 2. Act
        response = await client.get(
            "/resources/res1?user_id=user123"
            )
        
        # 3. Assert
        assert response.status_code == 200
        assert response.json()["name"] == "Integration Test Resource"

    finally:
        app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_get_resource_not_found(client, db_session):
    mock_authz = AsyncMock()
    mock_authz.check_permission.return_value = True
    
    app.dependency_overrides[get_current_user] = lambda: "user123"
    app.dependency_overrides[get_authz_service] = lambda: mock_authz
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        # 2. Act
        response = await client.get(
            "/resources/res2?user_id=user123"
            )
        
        # 3. Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Resource not found"
    finally:
        app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_get_resource_forbidden(client, db_session):

    # mock new item for ResourceDB
    resource = ResourceDB(
        id="res3", 
        name="Integration Test Resource", 
        description="...",
        resource_type="api"
    )

    db_session.add(resource)
    await db_session.commit()

    mock_authz = AsyncMock()
    mock_authz.check_permission.return_value = False
    
    app.dependency_overrides[get_current_user] = lambda: "user123"
    app.dependency_overrides[get_authz_service] = lambda: mock_authz
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        # 2. Act
        response = await client.get(
            "/resources/res3?user_id=user123"
            )
        
        # 3. Assert
        assert response.status_code == 403

        result = await db_session.execute(
            select(ResourceDB).where(ResourceDB.id== "res3")
            )
        
        assert result.scalar_one_or_none() is not None
    finally:
        app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_create_resource_success(client, db_session):

    mock_authz = AsyncMock()
    mock_authz.check_permission.return_value = True

    app.dependency_overrides[get_current_user] = lambda: "user123"
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_authz_service] = lambda: mock_authz

    try:
        # 2. Act
        response = await client.post(
            "/resources/?user_id=user123", 

            json={
                "name": "Integration Test Resource", 
                "description": "...", 
                "resource_type": "api"
                }
            )

        # 3. Assert
        assert response.status_code == 200
        assert response.json()["name"] == "Integration Test Resource"
    
    finally:
        app.dependency_overrides = {}
    

@pytest.mark.asyncio
async def test_list_resource(client, db_session):

    # 1. Arrange - Mock Database
    resource = ResourceDB(
        id="res4", 
        name="Integration Test Resource", 
        description="...",
        resource_type="api"
    )

    db_session.add(resource)
    await db_session.commit()

    # 2. Arrange - Mock Auth Service
    mock_authz = AsyncMock()
    mock_authz.get_user_resources.return_value = ["res4"]

    # 3. Apply Overrides
    app.dependency_overrides[get_current_user] = lambda: "user123"
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_authz_service] = lambda: mock_authz

    try:
        # 4. Act
        response = await client.get("/resources/?user_id=user123")
        
        # 5. Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "res4"
    finally:
        # Always cleanup
        app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_delete_resource_success(client, db_session):

    # 1. Arrange
    Resource = ResourceDB(id="res5", name="Resource 1", resource_type="api")
    db_session.add(Resource)
    await db_session.commit()

    mock_authz = AsyncMock()
    mock_authz.check_permission.return_value = True

    app.dependency_overrides[get_current_user] = lambda: "user123"
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_authz_service] = lambda: mock_authz

    try:
        # 2. Act
        response = await client.delete("/resources/res5?user_id=user123")

        # 3. Assert
        assert response.status_code == 200

        result = await db_session.execute(
            select(ResourceDB).where(ResourceDB.id =="res5")
            )

        assert result.scalar_one_or_none() is None
        
    finally:
        app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_delete_resource_not_found(client, db_session):

    mock_authz = AsyncMock()
    mock_authz.check_permission.return_value = True

    app.dependency_overrides[get_current_user] = lambda: "user123"
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_authz_service] = lambda: mock_authz

    try:
        # 2. Act
        response = await client.delete("/resources/res6?user_id=user123")

        # 3. Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Resource not found"
    finally:
        app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_delete_resource_forbidden(client, db_session):

    # 1. Arrange
    Resource = ResourceDB(id="res7", name="Resource 1", resource_type="api")
    db_session.add(Resource)
    await db_session.commit()


    mock_authz = AsyncMock()
    mock_authz.check_permission.return_value = False

    app.dependency_overrides[get_current_user] = lambda: "user123"
    app.dependency_overrides[get_authz_service] = lambda: mock_authz

    try:
        # 2. Act
        response = await client.delete("/resources/res7?user_id=user123")

        # 3. Assert
        assert response.status_code == 403
        assert response.json()["detail"] == "Admin access required"
    finally:
        app.dependency_overrides = {}

        