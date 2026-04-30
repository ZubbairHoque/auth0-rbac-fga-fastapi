from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from app.services.authorization_service import authz_service

router = APIRouter()

class UserAssignment(BaseModel):
    user_id: str = Field(..., description="User ID to assign")
    role: str = Field(..., description="Role: 'admin' or 'member'")

@router.post("/users")
async def assign_user_role(
    assignment: UserAssignment,
    admin_user_id: str = Query(..., description="Admin ID performing the action")
):
    """Assign a global role to a user (Admin only)."""
    # Check if the performing user is an admin
    if not await authz_service.check_permission(admin_user_id, "can_manage_users"):
        raise HTTPException(status_code=403, detail="Only admins can manage users")
    
    success = await authz_service.assign_user_role(assignment.user_id, assignment.role)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to assign role")
    
    return {"message": f"User {assignment.user_id} assigned to {assignment.role}"}

@router.delete("/users/{user_id}")
async def remove_user_role(
    user_id: str,
    role: str = Query(..., description="Role to remove ('admin' or 'member')"),
    admin_user_id: str = Query(..., description="Admin ID performing the action")
):
    """Remove a global role from a user (Admin only)."""
    if not await authz_service.check_permission(admin_user_id, "can_manage_users"):
        raise HTTPException(status_code=403, detail="Only admins can manage users")
    
    success = await authz_service.remove_user_role(user_id, role)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to remove role")
    
    return {"message": f"User {user_id} removed from {role}"}
