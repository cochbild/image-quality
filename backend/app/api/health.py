from fastapi import APIRouter
from app.services.lm_studio_client import LMStudioClient

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "iqa-backend"}


@router.get("/lm-studio/status")
async def lm_studio_status():
    client = LMStudioClient()
    healthy = await client.health_check()
    return {"connected": healthy, "url": client.base_url}


@router.get("/lm-studio/models")
async def lm_studio_models():
    client = LMStudioClient()
    try:
        models = await client.list_models()
        return {"models": models}
    except Exception as e:
        return {"models": [], "error": str(e)}
