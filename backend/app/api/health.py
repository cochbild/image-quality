from fastapi import APIRouter, Depends, Query

from app.core.auth import require_api_key
from app.services.lm_studio_client import LMStudioClient

router = APIRouter()


@router.get("/health")
async def health_check():
    # Kept unauthenticated so orchestrators (Docker, Compose, K8s probes) can reach it.
    return {"status": "healthy", "service": "iqa-backend"}


@router.get("/lm-studio/status", dependencies=[Depends(require_api_key)])
async def lm_studio_status():
    client = LMStudioClient()
    healthy = await client.health_check()
    return {"connected": healthy, "url": client.base_url}


@router.get("/lm-studio/models", dependencies=[Depends(require_api_key)])
async def lm_studio_models(vision_only: bool = Query(False, description="Only return vision-capable models")):
    client = LMStudioClient()
    try:
        models = await client.list_models(vision_only=vision_only)
        return {"models": models}
    except Exception as e:
        return {"models": [], "error": str(e)}
