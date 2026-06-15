import uuid
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.resource import Resource, ResourceCreate
from app.database import get_db, ResourceDB
from app.services.authorization_service import authz_service, AuthorizationService

router = APIRouter()

security = HTTPBearer()

def get_authz_service() -> AuthorizationService:
    return authz_service

async def get_current_user(
        token:HTTPAuthorizationCredentials= Depends(security)
        )-> str:
    
    """
    Extract Credentials from a bearer token from request header. 
    In a real app, you'd verify the token and extract claims.
    """

    # Extract Credentials from token
    return token.credentials

@router.get("/", response_model=List[Resource])
async def list_resources(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    authz: AuthorizationService = Depends(get_authz_service)
):
    """List all resources the user can view."""
    allowed_ids = await authz.get_user_resources(user_id)

    query = select(ResourceDB).where(ResourceDB.id.in_(allowed_ids))
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/{resource_id}", response_model=Resource)
async def get_resource(
    resource_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    authz: AuthorizationService = Depends(get_authz_service)
):
    """Get a specific resource."""
    if not await authz.check_permission(user_id, "can_view", resource_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = await db.execute(select(ResourceDB).where(ResourceDB.id == resource_id))
    resource_db = result.scalar_one_or_none()
    
    if not resource_db:
        raise HTTPException(status_code=404, detail="Resource not found")
    
    return resource_db

@router.post("/", response_model=Resource)
async def create_resource(
    resource: ResourceCreate,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    authz: AuthorizationService = Depends(get_authz_service)
):
    """Create a new resource (admin or member)."""
    if not await authz.check_permission(user_id, "can_create_resource"):
        raise HTTPException(
            status_code=403, detail="Permission denied to create resources"
            )
    
    resource_id = str(uuid.uuid4())
    resource_db = ResourceDB(
        id=resource_id,
        name=resource.name,
        description=resource.description,
        resource_type=resource.resource_type
    )
    
    db.add(resource_db)
    await db.commit()
    await db.refresh(resource_db)
    
    await authz.link_resource_to_system(resource_id)
    
    return resource_db

@router.delete("/{resource_id}")
async def delete_resource(
    resource_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    authz: AuthorizationService = Depends(get_authz_service)
):
    """Delete a resource (admin only)."""
    if not await authz.check_permission(user_id, "can_delete", resource_id):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.execute(select(ResourceDB).where(ResourceDB.id == resource_id))
    resource_db = result.scalar_one_or_none()
    
    if not resource_db:
        raise HTTPException(status_code=404, detail="Resource not found")
    
    await db.delete(resource_db)
    await db.commit()
    
    return {"message": "Resource deleted successfully"}
