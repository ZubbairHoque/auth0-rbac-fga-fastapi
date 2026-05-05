from openfga_sdk import OpenFgaClient
from openfga_sdk.client import ClientConfiguration
from openfga_sdk.client.models import ClientCheckRequest, ClientWriteRequest, ClientTuple
from openfga_sdk.credentials import Credentials, CredentialConfiguration
from app.config import settings
import logging
from typing import Optional

# Set up logging
logger = logging.getLogger(__name__)

class Auth0FGAClient:
    def __init__(self):
        self._client: Optional[OpenFgaClient] = None

    def _get_client(self) -> OpenFgaClient:
        """Lazily initialize the OpenFgaClient."""
        if self._client is None:
            # Get Auth0 FGA configuration from settings
            store_id = settings.auth0_fga_store_id or "dummy-store"
            client_id = settings.auth0_fga_client_id or "dummy-client"
            client_secret = settings.auth0_fga_client_secret or "dummy-secret"

            configuration = ClientConfiguration(
                api_url=settings.auth0_fga_api_url or "https://api.us1.fga.dev",
                store_id=store_id,
                authorization_model_id=settings.auth0_fga_authorization_model_id,
                credentials= Credentials(
                    method="client_credentials",
                    configuration= CredentialConfiguration(
                        client_id=client_id,
                        client_secret=client_secret,
                        api_audience= settings.auth0_fga_api_audience,
                        api_issuer= settings.auth0_fga_api_token_issuer
                    )
                )
            )
            self._client = OpenFgaClient(configuration)
        return self._client

    async def check_permission(self, user: str, relation: str, object_id: str) -> bool:
        """Check if a user has a specific relation to an object."""
        try:
            client = self._get_client()
            response = await client.check(ClientCheckRequest(
                user=user,
                relation=relation,
                object=object_id
            ))
            logger.debug(f"Permission check result: {response.allowed}")
            return response.allowed
        except Exception as e:
            logger.error(f"Error checking permission: {e}")
            return False

    async def write_tuples(self, tuples: list[ClientTuple]) -> bool:
        """Write relationship tuples to Auth0 FGA."""
        try:
            client = self._get_client()
            write_request = ClientWriteRequest(writes=tuples)
            await client.write(write_request)
            return True
        except Exception as e:
            logger.error(f"Error writing tuples: {e}")
            return False

    async def delete_tuples(self, tuples: list[ClientTuple]) -> bool:
        """Delete relationship tuples from Auth0 FGA."""
        try:
            client = self._get_client()
            write_request = ClientWriteRequest(deletes=tuples)
            await client.write(write_request)
            return True
        except Exception as e:
            logger.error(f"Error deleting tuples: {e}")
            return False
    
    async def list_objects(self, user: str, relation: str, object_type: str) -> list[str]:
        """List all objects of a given type."""
        try:
            client = self._get_client()
            # pyrefly: ignore [missing-argument]
            response = await client.list_objects(
                # pyrefly: ignore [unexpected-keyword]
                user=user,
                # pyrefly: ignore [unexpected-keyword]
                relation=relation,
                # pyrefly: ignore [unexpected-keyword]
                type=object_type
            )
            return response.objects if hasattr(response, 'objects') else []
        except Exception as e:
            logger.error(f"Error listing objects: {e}")
            return []
    
    async def health_check(self) -> bool:
        """Check if the Auth0 FGA service is healthy."""
        try:
            client = self._get_client()
            await client.read_authorization_models()
            return True
        except Exception as e:
            logger.error(f"Auth0 FGA health check failed: {e}")
            return False

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client is not None:
            await self._client.close()
            self._client = None


# Global client instance (now safe to import anywhere)
fga_client = Auth0FGAClient()
