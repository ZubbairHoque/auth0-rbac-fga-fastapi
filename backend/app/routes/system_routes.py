import uuid

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.authorization_service import authz_service, AuthorizationService
from app.models.invitation import InvitationCreate, Auth0RegistrationPayLoad
from app.database import InvitationDB, get_db
from sqlalchemy import select


router = APIRouter()

def get_authz_service() -> AuthorizationService:
    return authz_service

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
    # Check if the performing user is an admin
    if not await authz.check_permission(admin_user_id, "can_manage_users"):
        raise HTTPException(status_code=403, detail="Only admins can manage users")
    
    success = await authz.assign_user_role(assignment.user_id, assignment.role)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to assign role")
    
    return {"message": f"User {assignment.user_id} assigned to {assignment.role}"}

@router.delete("/users/{user_id}")
async def remove_user_role(
    user_id: str,
    role: str = Query(..., description="Role to remove ('admin' or 'member')"),
    admin_user_id: str = Query(..., description="Admin ID performing the action"),
    authz: AuthorizationService = Depends(get_authz_service)
):
    """Remove a global role from a user (Admin only)."""
    if not await authz.check_permission(admin_user_id, "can_manage_users"):
        raise HTTPException(status_code=403, detail="Only admins can manage users")
    
    success = await authz.remove_user_role(user_id, role)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to remove role")
    
    return {"message": f"User {user_id} removed from {role}"}

@router.post("/invite")
async def invite_user_as_admin(
    invitation: InvitationCreate,
    admin_user_id: str = Query(..., description="Admin ID performing the action"),
    authz: AuthorizationService = Depends(get_authz_service),
    db: AsyncSession = Depends(get_db)
):
    """Endpoint for new admins"""

    # check if requester is admin
    if not await authz.check_permission(admin_user_id, "can_manage_users"):
        raise HTTPException(
            status_code=403, detail="Only admins can send invitations"
            )
    
    # create an invitation in the database
    new_inv = InvitationDB(
        email=invitation.email, 
        role=invitation.role, 
        token=str(uuid.uuid4())
    )
    
    db.add(new_inv)
    await db.commit()
    await db.refresh(new_inv)
    return new_inv 

@router.post("/auth/webhook/post-registration")
async def sync_user_to_fga(
    payload: Auth0RegistrationPayLoad,
    authz: AuthorizationService = Depends(get_authz_service),
    db: AsyncSession = Depends(get_db)
):
    """Webhook to sync new users from Auth0 to FGA."""

    user_id = payload.user_id
    email = payload.email

    # Check if there's an invitation for this email
    result = await db.execute(
        select(InvitationDB).where(InvitationDB.email == email)
    )
    
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(
            status_code=404, detail="No invitation found for this email"
        )

    if invitation.is_used:
        raise HTTPException(
            status_code=400, detail="Invitation has already been used"
        )

    # Sync user to FGA with the role from the invitation
    success = await authz.assign_user_role(user_id, invitation.role)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to assign role in FGA")

    # Mark the invitation as used
    invitation.is_used = True
    await db.commit()

    return {
        "message": f"User with email {email} synced to FGA with role {invitation.role}"
    }
