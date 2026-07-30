def extract_error(response):
    """Return the backend-provided error detail, falling back to raw text."""
    try:
        payload = response.json()
        if isinstance(payload, dict) and "detail" in payload:
            return payload["detail"]
    except Exception:
        pass
    return response.text