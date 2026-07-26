from fastapi.exceptions import HTTPException
from app.core.security import verify_auth0_token
from unittest.mock import MagicMock
from unittest.mock import patch
import time
import pytest
import jwt
import hmac
import hashlib

from app.core.security import verify_signature

def test_valid_signature_success():
    """Verify the HMAC signature of incoming raw bytes."""
    
    # setup object secret and raw_body
    secret = "mysecret".encode("utf-8")
    raw_body = b"raw body"

    # run through the hashing algorithm
    expected_signature = hmac.new(
        secret, raw_body, hashlib.sha256
        ).hexdigest()

    # check if the expected_signature matches the raw body's signature
    assert verify_signature(raw_body, "mysecret", expected_signature)    


def test_invalid_signature_fail():
    """Verify the HMAC signature of incoming raw bytes."""
    raw_body = b"raw body"
    secret = "mysecret"

    # check if the signature is valid
    assert not verify_signature(raw_body, secret, "invalid_signature")

@pytest.mark.asyncio
@patch("app.core.security.jwt.decode")
@patch("app.core.security.jwks_client.get_signing_key_from_jwt")
async def test_verify_valid_signature_success(
    mock_get_key, mock_decode
    ):
    """return test_token as decoded token"""
    mock_signing_key = MagicMock()

    mock_signing_key.private_key = "fakekey"
    mock_get_key.return_value = mock_signing_key

    mock_payload = {
        "sub": "user123", 
        "aud": "http://test.audience.com", 
        "exp": time.time() + 600
    }

    mock_decode.return_value = mock_payload

    result = await verify_auth0_token("some_fake_token_string")
    
    assert result == mock_payload

    

@pytest.mark.parametrize(
    "exception_class",
    [
        jwt.InvalidSignatureError("Invalid signature"),
        jwt.InvalidTokenError("Invalid token"),
        jwt.ExpiredSignatureError("Token has expired"),
    ],
)
@patch("app.core.security.jwt.decode")
@patch("app.core.security.jwks_client.get_signing_key_from_jwt")
async def test_verify_invalid_signature_fail(
    mock_get_key, mock_decode, exception_class
    ):
    """test for the verification of an invalid signature"""
    mock_signing_key = MagicMock()

    mock_signing_key.private_key = "fakekey"
    mock_get_key.return_value = mock_signing_key
    
    mock_decode.side_effect = exception_class

    with pytest.raises(HTTPException) as exc_info:
        await verify_auth0_token("some_fake_token_string")

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == exception_class.args[0]


    
