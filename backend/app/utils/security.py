import hmac
import hashlib 
from fastapi import HTTPException
from app.config import settings
import jwt

jwks_url = f"https://{settings.auth0_fga_domain}/.well-known/jwks.json"

# Initialise the JWK Client
jwks_client = jwt.PyJWKClient(jwks_url)

def verify_signature(raw_body: bytes, secret: str, signature: str) -> bool:
    """
    Verify the HMAC signature of incoming raw bytes.
    """
    if not secret or not signature:
        return False

    # Calculate expected signature
    expected_signature = hmac.new(
        key=secret.encode("utf-8"),
        msg=raw_body,
        digestmod=hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_signature, signature)

async def verify_auth0_token(token: str) -> dict:
    """
    Verify the Auth0 token using the public key from the JWKS endpoint.
    """

    try:

        # Automatically find the signing key matching the token's 'kid'
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        # Decode and securely verify the token using that public key
        data = jwt.decode(
            token, 
            signing_key.key, 
            algorithms=[settings.algorithm], 
            audience=settings.auth0_fga_api_audience,
            issuer=f"https://{settings.auth0_fga_domain}/"
        )

        return data

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidSignatureError:
        raise HTTPException(status_code=401, detail="Invalid signature")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    