import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Header, Query, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.authorization_service import authz_service, AuthorizationService
from app.models.invitation import InvitationCreate, Auth0RegistrationPayLoad, Invitation
from app.database import InvitationDB, get_db
from app.utils.security import verify_signature
from app.config import settings

router = APIRouter()

def get_authz_service() -> AuthorizationService:
    return authz_service

# --- SECURITY GUARD ---

async def validate_webhook_signature(
    request: Request, 
    x_auth0_signature: str = Header(None)
):
    """
    Bouncer: Checks the signature before the route logic runs.
    Uses raw request body to ensure integrity.
    """
    if not x_auth0_signature:
        raise HTTPException(status_code=401, detail="Webhook signature missing")
        
    body = await request.body()
    if not verify_signature(body, settings.webhook_signature_secret, x_auth0_signature):
        raise HTTPException(status_code=403, detail="Invalid webhook signature")

# --- ROUTES ---

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

@router.post("/invite", response_model=Invitation)
async def invite_user(
    invitation_in: InvitationCreate,
    admin_user_id: str = Query(..., description="Admin ID performing the action"),
    authz: AuthorizationService = Depends(get_authz_service),
    db: AsyncSession = Depends(get_db)
):
    """Create a pending invitation for a new user (Admin only)."""
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
            InvitationDB.is_used == False
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
    await db.commit()

    return {"message": f"Successfully synced {payload.email} to FGA"}
