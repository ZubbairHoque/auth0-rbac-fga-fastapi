import hmac
import hashlib

def verify_signature(raw_body: bytes, secret: str, signature: str) -> bool:
    """
    Verify the HMAC signature of incoming raw bytes.
    Pure Python utility - no FastAPI dependencies.
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
