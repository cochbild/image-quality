from urllib.parse import urlparse

from fastapi import HTTPException

_BLOCKED_METADATA_HOSTS = {
    "169.254.169.254",
    "metadata.google.internal",
    "metadata.azure.com",
    "metadata",
    "fd00:ec2::254",
}


def validate_outbound_url(url: str) -> None:
    """Reject URLs that are malformed, use a non-HTTP scheme, or point at a
    cloud-metadata endpoint.

    Loopback and RFC1918 addresses are allowed on purpose: the intended
    deployment talks to a local LM Studio or a HomeHub backend on the same
    Docker network.
    """
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    try:
        parsed = urlparse(url)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid URL")
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Only http(s) URLs are allowed")
    if not parsed.hostname:
        raise HTTPException(status_code=400, detail="URL must include a hostname")
    if parsed.hostname.lower() in _BLOCKED_METADATA_HOSTS:
        raise HTTPException(status_code=400, detail="URL targets a cloud metadata endpoint")
