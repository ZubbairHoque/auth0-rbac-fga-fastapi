from fastapi import APIRouter, Depends, HTTPException

from app.services.authorization_service import AuthorizationService, authz_service

router = APIRouter()

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
