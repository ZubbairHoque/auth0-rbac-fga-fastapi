import tracemalloc
from app.modules.member.schema import MemberBase
from app.modules.member.routes import get_authz_service, validate_webhook_signature
from app.modules.member.model import MemberDB, InvitationDB
from app.core.database import get_db
from app.modules.member.schema import MemberStatus
from sqlalchemy import select
from unittest.mock import AsyncMock, MagicMock, patch
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

@pytest.mark.asyncio
async def test_remove_user_role_for_active_user_success( client, db_session):
    mock_authz = AsyncMock()
    mock_authz.check_permission.return_value = True

    db_session.add(
        MemberDB(
            id="mem-2",
            email="brian@example.com", 
            role="admin", 
            status=MemberStatus.active,
            auth0_user_id="brian"
        )
    )

    await db_session.commit()

    member = await db_session.execute(
        select(MemberDB).where(MemberDB.email == "brian@example.com")
    )
    member = member.scalar_one_or_none()
    
    mock_authz.remove_user_role.return_value = True
    
    app.dependency_overrides[get_authz_service] = lambda: mock_authz
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db

    try:
        response = await client.delete(
            f"/members/{member.id}?role=admin&admin_user_id=boss"
            )

        assert response.status_code == 200
        
        assert member.status == MemberStatus.removed

        assert response.json()["message"] == f"User {member.id} removed from {member.role}"
    finally:
        app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_remove_user_role_for_invited_user_success(
    client, db_session
):
    mock_authz = AsyncMock()
    mock_authz.check_permission.return_value = True

    db_session.add(
        MemberDB(
            id="mem-3",
            email="alex@example.com", 
            role="admin", 
            status=MemberStatus.invited,
            auth0_user_id="alex"
        )
    )

    await db_session.commit()

    member = await db_session.execute(
        select(MemberDB).where(MemberDB.email == "alex@example.com")
    )
    member = member.scalar_one_or_none()
        
    app.dependency_overrides[get_authz_service] = lambda: mock_authz
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db

    try:
        response = await client.delete(
            f"/members/{member.id}?role=admin&admin_user_id=boss"
            )

        assert response.status_code == 200
        
        assert member.status == MemberStatus.removed

        mock_authz.remove_user_role.assert_not_called()

        assert response.json()["message"] == f"User {member.id} removed from {member.role}"
    finally:
        app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_remove_user_role_for_removed_user_fail( client, db_session):
    mock_authz = AsyncMock()
    mock_authz.check_permission.return_value = True

    db_session.add(
        MemberDB(
            id="mem-4",
            email="carl@example.com",
            role="admin", 
            status=MemberStatus.removed,
            auth0_user_id="carl"
        )
    )

    await db_session.commit()

    member = await db_session.execute(
        select(MemberDB).where(MemberDB.email == "carl@example.com")
    )
    member = member.scalar_one_or_none()
    
    mock_authz.remove_user_role.return_value = True
    
    app.dependency_overrides[get_authz_service] = lambda: mock_authz
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db

    try:
        response = await client.delete(
            f"/members/{member.id}?role=admin&admin_user_id=boss"
            )

        assert response.status_code == 400
        assert response.json()["detail"] == "Member is already removed"
    finally:
        app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_remove_user_not_found(client, db_session):
    mock_authz = AsyncMock()
    mock_authz.check_permission.return_value = True
    
    app.dependency_overrides[get_authz_service] = lambda: mock_authz
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db

    try:
        response = await client.delete(
            "/members/notmember?role=admin&admin_user_id=boss"
            )

        assert response.status_code == 404
        assert response.json()["detail"] == "Member not found"
    finally:
        app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_remove_user_forbidden(client):
    mock_authz = AsyncMock()
    mock_authz.check_permission.return_value = False
    mock_authz.remove_user_role.return_value = False
    
    app.dependency_overrides[get_authz_service] = lambda: mock_authz

    try:
        response = await client.delete(
            "/members/notmember?role=admin&admin_user_id=boss"
            )

        assert response.status_code == 403
        assert response.json()["detail"] == "Only admins can manage users"
    finally:
        app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_invite_user_success(client, db_session):
    mock_authz = AsyncMock()

    mock_authz.check_permission.return_value = True

    app.dependency_overrides[get_authz_service] = lambda: mock_authz
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db

    try:
        payload = {"email": "tobey@example.com", "role": "admin"}
        response = await client.post(
            "/members/invite?admin_user_id=boss",
            json=payload
        )

        assert response.status_code == 200

        body = response.json()
        assert body["email"] == "tobey@example.com"
        assert body["role"] == "admin"
        assert body["is_used"] is False

        result_invitation = await db_session.execute(
            select(InvitationDB).where(
                InvitationDB.email == "tobey@example.com"
            )
        )

        invitation = result_invitation.scalar_one_or_none()

        result_member = await db_session.execute(
            select(MemberDB).where(
                MemberDB.email == "tobey@example.com"
            )
        )

        member = result_member.scalar_one_or_none()

        assert invitation is not None
        assert invitation.email == "tobey@example.com"
        assert invitation.role == "admin"
        assert invitation.is_used is False

        assert member is not None
        assert member.email == "tobey@example.com"
        assert member.role == "admin"
        assert member.status == MemberStatus.invited

    finally:
        app.dependency_overrides = {}
        
@pytest.mark.asyncio
async def test_webhook_sync_success(client, db_session):
    mock_webhook_guard = AsyncMock()
    mock_authz = AsyncMock()
    
    # 1. Mock DB finding an in`vitation
    db_session.add(InvitationDB(
        id="inv1", email="test@example.com", role="admin", is_used=False)
    )

    # 2. Mock DB member being given access to members dashboard


    await db_session.commit()
    
    # 3. Mock FGA success
    mock_authz.assign_user_role.return_value = True

    # 4. Bypass the Bouncer
    app.dependency_overrides[validate_webhook_signature] = lambda: mock_webhook_guard    
    app.dependency_overrides[get_authz_service] = lambda: mock_authz
    app.dependency_overrides[get_db] = lambda: db_session
    
    try:

        response = await client.post(
            "/members/auth/webhook/post-registration",
            json={"user_id": "auth0|123", "email": "test@example.com"}
        )

        assert response.status_code == 200

        # assert invitation item is created
        result = await db_session.execute(
            select(InvitationDB).where(InvitationDB.email == "test@example.com")
        )

        invitation = result.scalar_one_or_none()
        
        assert "Successfully synced test@example.com to FGA" in response.json()[
            "message"
        ]
        
        # Assert the webhook consumed the pending invitation.
        assert invitation is not None
        assert invitation.id == "inv1"
        assert invitation.email == "test@example.com"
        assert invitation.role == "admin"
        assert invitation.is_used is True

        
    finally:
        app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_webhook_sync_no_invitation(client, db_session):
    mock_webhook_guard = AsyncMock() # Need the bouncer bypass!
    mock_authz = AsyncMock()
        
    app.dependency_overrides[validate_webhook_signature] = lambda: mock_webhook_guard
    app.dependency_overrides[get_authz_service] = lambda: mock_authz
    app.dependency_overrides[get_db] = lambda: db_session
    
    try:
        payload = {"email": "stranger@example.com", "user_id": "auth0|123"}
        response = await client.post(
            "/members/auth/webhook/post-registration", json=payload
        )

        # Should be 404 (Not Found), not 401 (Unauthorized)
        assert response.status_code == 404
        assert response.json()["detail"] == "No pending invitation found"
    finally:
        app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_get_members_success(client, db_session):
    mock_authz = AsyncMock()

    # arrange
    db_session.add_all([

        # Active member mock
        MemberDB(
            id="member1", email="peter@example.com", role="admin", status=MemberStatus.active
        ),

        # invited/unactive member mock
        MemberDB(
            id="member2", email="bob@example.com", role="member", status=MemberStatus.invited
        ),

        # removed member mock
        MemberDB(
            id="member3", email="charlie@example.com", role="admin", status=MemberStatus.removed
        ),

    ])
    await db_session.commit()

    mock_authz.check_permission.return_value = True

    app.dependency_overrides[get_authz_service] = lambda: mock_authz
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db

    try:

        # 3. Act
        response = await client.get(
            "/members/?admin_user_id=boss"
        )

        data = response.json()

        # 4. Assert
        assert response.status_code == 200

        statuses_by_email = {member["email"]: member["status"] for member in data}

        assert statuses_by_email["peter@example.com"] == "active"
        assert statuses_by_email["bob@example.com"] == "invited"

        # Should return 2 members (active + invited, excluding removed)
        assert len(data) == 2

        assert {member["email"] for member in data} == {
            "bob@example.com", "peter@example.com"
        }

        assert "charlie@example.com" not in {member["email"] for member in data}

    finally:
        app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_get_members_fail(client, db_session):
    mock_authz = AsyncMock()
    mock_authz.check_permission.return_value = False
    
    app.dependency_overrides[get_authz_service] = lambda: mock_authz
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db

    try:
        # 2. Act
        response = await client.get(
            "/members/?admin_user_id=boss"
        )

        # 3. Assert
        assert response.status_code == 403
        assert response.json()["detail"] == "Only admins can manage users"
    finally:
        app.dependency_overrides = {}