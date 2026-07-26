from fastapi import APIRouter, HTTPException, Header, Query, Depends, Request
from pydantic import BaseModel, Field

from app.modules.auth_fga.service import AuthorizationService, authz_service
from app.core.security import verify_signature
from app.core.config import settings

router = APIRouter()
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



