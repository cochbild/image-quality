import hmac

from fastapi import Header, HTTPException

from app.core.config import settings


async def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    """FastAPI dependency that enforces a shared-secret API key on every call.

    The expected key comes from settings.IQA_API_KEY. Startup fails if that
    value is empty, so reaching this dependency guarantees a configured key.
    """
    if not x_api_key or not hmac.compare_digest(x_api_key.encode(), settings.IQA_API_KEY.encode()):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
