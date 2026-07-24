from sqlalchemy import update
from httpx import delete
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Header, Query, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.modules.member.model import MemberDB, InvitationDB
from app.modules.member.schema import InvitationCreate, Auth0RegistrationPayLoad, Invitation, Member, MemberStatus
from app.modules.auth_fga.service import AuthorizationService, authz_service
from app.core.database import get_db
from app.core.security import verify_signature
from app.core.config import settings

router = APIRouter()

def get_authz_service() -> AuthorizationService:
    return authz_service

@router.get("/health")
async def health_check():
    """Check the health of the Auth0 FGA connection."""
    fga_healthy = await authz_service.check_auth0_fga_health()
    if fga_healthy:
        return {"status": "ok", "message": "Auth0 FGA connection is healthy"}
    else:
        return {"status": "error", "message": "Auth0 FGA connection failed"}

def get_authz_service() -> AuthorizationService:
    return authz_service

@router.get("/validate/{dashboard_type}")
async def access_dashboard(
    user_id: str, 
    dashboard_type: str,
    authz: AuthorizationService = Depends(get_authz_service)
):
    """
    Check if a user has access to a specific dashboard type.
    """
    if not await authz.validate_dashboard_access(user_id, dashboard_type):
        raise HTTPException(
            status_code=403, 
            detail=f"Access denied to {dashboard_type} dashboard."
        )
    
    return {"authorized": True}

class UserAssignment(BaseModel):
    user_id: str = Field(..., description="User ID to assign")
    role: str = Field(..., description="Role: 'admin' or 'member'")

@router.post("/users")
async def assign_user_role(
    assignment: UserAssignment,
    admin_user_id: str = Query(..., description="Admin ID performing the action"),
    authz: AuthorizationService = Depends(get_authz_service)
):
    """Assign a global role to a user (Admin only)."""
    if not await authz.check_permission(admin_user_id, "can_manage_users"):
        raise HTTPException(status_code=403, detail="Only admins can manage users")
        
    # assign user privilege
    success = await authz.assign_user_role(assignment.user_id, assignment.role)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to assign role")
    
    return {"message": f"User {assignment.user_id} assigned to {assignment.role}"}

@router.delete("/members/{member_id}")
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

