from typing import List, Optional
from openfga_sdk.client.models import ClientTuple
from app.utils.auth0_fga_client import fga_client

ROLES = ["admin", "member"]

class AuthorizationService:
    """
    RBAC authorization service using Auth0 FGA for a Single-Tenant System.
    """

    # The single anchor for our entire internal application
    SYSTEM_ID = "main"
    SYSTEM_OBJ = f"system:{SYSTEM_ID}"

    async def assign_user_role(self, user_id: str, role: str) -> bool:
        """Assign a global role (admin/member) to the user."""
        if role not in ROLES:
            raise ValueError(f"Role must be in: {ROLES}")
            
        return await fga_client.write_tuples([
            ClientTuple(
                user=f"user:{user_id}",
                relation=role,
                object=self.SYSTEM_OBJ
            )
        ])

    async def remove_user_role(self, user_id: str, role: str) -> bool:
        """Remove a global role from the user."""
        if role not in ROLES:
            raise ValueError(f"Role must be in: {ROLES}")
            
        return await fga_client.delete_tuples([
            ClientTuple(
                user=f"user:{user_id}",
                relation=role,
                object=self.SYSTEM_OBJ
            )
        ])

    async def link_resource_to_system(self, resource_id: str) -> bool:
        """Link a resource to the global system so it inherits permissions."""
        return await fga_client.write_tuples([
            ClientTuple(
                user=self.SYSTEM_OBJ,
                relation="workspace",
                object=f"resource:{resource_id}"
            )
        ])

    async def check_permission(
            self, 
            user_id: str, 
            action: str, 
            resource_id: Optional[str] = None
            ) -> bool:
        
        """
        Check if user is allowed to perform an action on a resource or the system.
        """

        target_obj = f"resource:{resource_id}" if resource_id else self.SYSTEM_OBJ
        
        return await fga_client.check_permission(
            user=f"user:{user_id}",
            relation=action,
            object_id=target_obj
        )
    
    async def validate_dashboard_access(
            self, user_id: str, dashboard_type: str,
            ) -> bool:
        
        """
        Dynamically checks dashboard access based on the provided type.
        This leverages the FGA model rules defined in Step 1.
        """
       
        relation = f"can_access_{dashboard_type}_dashboard"
        return await self.check_permission(user_id, relation)
   
    async def get_user_resources(self, user_id: str) -> List[str]:
        """Get all resource IDs a user can view."""
        results = await fga_client.list_objects(
            user=f"user:{user_id}",
            relation="can_view",
            object_type="resource"
        )
        return [res.replace("resource:", "") for res in results]




    async def check_auth0_fga_health(self) -> bool:
        """Check if Auth0 FGA service is healthy."""
        return await fga_client.health_check()

# Global authorization service instance
authz_service = AuthorizationService()
