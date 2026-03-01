import base64
import httpx
from pathlib import Path
from typing import Optional
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("lm_studio")


class LMStudioClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.LM_STUDIO_URL).rstrip("/")

    async def list_models(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.base_url}/models")
            resp.raise_for_status()
            return resp.json().get("data", [])

    async def analyze_image(self, image_path: str, prompt: str, model: Optional[str] = None) -> str:
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        suffix = path.suffix.lower().lstrip(".")
        mime_map = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp", "gif": "gif"}
        mime_type = f"image/{mime_map.get(suffix, suffix)}"

        image_data = base64.b64encode(path.read_bytes()).decode("utf-8")

        # Resolve model: parameter > DB setting > first available
        if not model:
            model = await self._get_default_model()

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_data}"}},
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
            "max_tokens": 2048,
            "temperature": 0.1,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{self.base_url}/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def _get_default_model(self) -> str:
        models = await self.list_models()
        if not models:
            raise RuntimeError("No models loaded in LM Studio")
        return models[0]["id"]

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/models")
                return resp.status_code == 200
        except Exception:
            return False
