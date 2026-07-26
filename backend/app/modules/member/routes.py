import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException,  Query, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.modules.auth_fga.service import  AuthorizationService
from app.modules.auth_fga.routes import get_authz_service
from app.modules.member.schema import InvitationCreate, Auth0RegistrationPayLoad, Invitation, Member, MemberStatus
from app.modules.auth_fga.routes import validate_webhook_signature
from app.modules.member.model import MemberDB, InvitationDB
from app.core.database import get_db

router = APIRouter()

# --- ROUTES ---

class UserAssignment(BaseModel):
    user_id: str = Field(..., description="Use ID to assign")
    role: str = Field(..., description="Role: 'admin' or 'member'")

@router.delete("/{member_id}")
async def remove_user_role(
    member_id: str,
    role: str = Query(..., description="Role to remove ('admin' or 'member')"),
    admin_user_id: str = Query(..., description="Admin ID performing the action"),
    db: AsyncSession = Depends(get_db),
    authz: AuthorizationService = Depends(get_authz_service)
):
    """Remove a global role from a user (Admin only)."""
    if not await authz.check_permission(admin_user_id, "can_manage_users"):
        raise HTTPException(status_code=403, detail="Only admins can manage users")

    # check if there is a member 
    member = await db.scalar(
        select(MemberDB).where(MemberDB.id == member_id)
    )

    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    if member.status == MemberStatus.active:
        member.status = MemberStatus.removed

        await authz.remove_user_role(member.auth0_user_id, member.role)

    elif member.status == MemberStatus.invited:
        member.status = MemberStatus.removed

    # if member is already removed, raise error
    elif member.status == MemberStatus.removed:
        raise HTTPException(
            status_code=400, detail="Member is already removed"
        )

    else:
        raise HTTPException(
            status_code=400, detail="Invalid member status"
        )

    await db.commit()
    return {"message": f"User {member_id} removed from {role}"}

@router.post("/invite", response_model=Invitation)
async def invite_user(
    invitation_in: InvitationCreate,
    admin_user_id: str = Query(..., description="Admin ID performing the action"),
    authz: AuthorizationService = Depends(get_authz_service),
    db: AsyncSession = Depends(get_db)
):
    """Create a pending invitation for a new user (Admin only)."""

    # check for admin role
    if not await authz.check_permission(admin_user_id, "can_manage_users"):
        raise HTTPException(status_code=403, detail="Only admins can send invitations")    

    
    # Explicitly set defaults to ensure Pydantic validation passes even with Mocks
    new_inv = InvitationDB(
        id=str(uuid.uuid4()),
        email=invitation_in.email, 
        role=invitation_in.role, 
        token=str(uuid.uuid4()),
        is_used=False,
        created_at=datetime.now(timezone.utc)
    )
    
    db.add(new_inv)    

    # create new member

    new_member = MemberDB(
        id=str(uuid.uuid4()),
        email=new_inv.email,
        role=new_inv.role,
        status=MemberStatus.invited
    )
    
    db.add(new_member)

    await db.commit()
    await db.refresh(new_inv)
    
    return new_inv


@router.post("/auth/webhook/post-registration")
async def sync_user_to_fga(
    payload: Auth0RegistrationPayLoad,
    _ = Depends(validate_webhook_signature), # The Guard
    authz: AuthorizationService = Depends(get_authz_service),
    db: AsyncSession = Depends(get_db)
):
    """Webhook triggered by Auth0 to sync a new user to FGA after registration."""
    
    # Check if there's a pending invitation
    result = await db.execute(
        select(InvitationDB).where(
            InvitationDB.email == payload.email,
            InvitationDB.is_used.is_(False)
        )
    )
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(status_code=404, detail="No pending invitation found")

    # Assign role in FGA
    success = await authz.assign_user_role(payload.user_id, invitation.role)
    if not success:
        raise HTTPException(status_code=500, detail="FGA assignment failed")

    # Finalize invitation
    invitation.is_used = True
    
    # find member details
    result_mem = await db.execute(
        select(MemberDB).where(MemberDB.email == payload.email)
    )
    member = result_mem.scalar_one_or_none()
    
    if not member:
        # do the FGA assignment and mark the invitation used without error
        await db.commit()
        return {"message": f"Successfully synced {payload.email} to FGA"}
    
    # update member
    member.auth0_user_id = payload.user_id
    member.status = MemberStatus.active
    await db.commit()

    return {"message": f"Successfully synced {payload.email} to FGA"}

@router.get("/", response_model=list[Member])
async def get_members(
    admin_user_id: str = Query(..., description="Admin ID performing the action"),
    authz: AuthorizationService = Depends(get_authz_service),
    db: AsyncSession = Depends(get_db)
):
    """Get a list of members (Admin only)."""
    if not await authz.check_permission(admin_user_id, "can_manage_users"):
        raise HTTPException(status_code=403, detail="Only admins can manage users")

    # Get all users who aren't labeled as removed
    query = select(MemberDB).where(MemberDB.status  != MemberStatus.removed) # Removed members stay in the table for history but are hidden from the dashboard list.
    result = await db.execute(query)
    members = result.scalars().all()

    return members