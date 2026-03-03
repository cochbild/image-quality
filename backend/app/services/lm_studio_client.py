import base64
import io
import httpx
from pathlib import Path
from typing import Optional
from PIL import Image
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("lm_studio")

# Max dimension for images sent to the model (keeps payload manageable for local LLMs)
MAX_IMAGE_DIMENSION = 768


class LMStudioClient:
    def __init__(self, base_url: Optional[str] = None):
        url = (base_url or settings.LM_STUDIO_URL).rstrip("/")
        # Ensure URL ends with /v1 for OpenAI-compatible endpoint
        if not url.endswith("/v1"):
            url = url + "/v1"
        self.base_url = url

    async def list_models(self, vision_only: bool = False) -> list[dict]:
        """List available models. Uses LM Studio native API for richer metadata when available."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try LM Studio native API first (has type field: vlm vs llm)
            native_url = self.base_url.replace("/v1", "/api/v0") + "/models"
            try:
                resp = await client.get(native_url)
                if resp.status_code == 200:
                    models = resp.json().get("data", [])
                    if vision_only:
                        models = [m for m in models if m.get("type") == "vlm"]
                    return models
            except Exception:
                pass
            # Fall back to OpenAI-compatible endpoint
            resp = await client.get(f"{self.base_url}/models")
            resp.raise_for_status()
            models = resp.json().get("data", [])
            if vision_only:
                vision_keywords = {"vl", "vision", "visual"}
                models = [m for m in models if any(kw in m["id"].lower() for kw in vision_keywords)]
            return models

    async def analyze_image(self, image_path: str, prompt: str, model: Optional[str] = None) -> str:
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        # Resize large images to avoid context length overflow (400 errors)
        img = Image.open(path)
        w, h = img.size
        if max(w, h) > MAX_IMAGE_DIMENSION:
            ratio = MAX_IMAGE_DIMENSION / max(w, h)
            new_size = (int(w * ratio), int(h * ratio))
            img = img.resize(new_size, Image.LANCZOS)
            logger.info(f"Resized {path.name} from {w}x{h} to {new_size[0]}x{new_size[1]}")

        # Encode as JPEG for smaller base64 payload
        buf = io.BytesIO()
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.save(buf, format="JPEG", quality=85)
        image_data = base64.b64encode(buf.getvalue()).decode("utf-8")
        mime_type = "image/jpeg"

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
        # Prefer vision models for image analysis
        vision_models = await self.list_models(vision_only=True)
        if vision_models:
            # Prefer a loaded model
            loaded = [m for m in vision_models if m.get("state") == "loaded"]
            return loaded[0]["id"] if loaded else vision_models[0]["id"]
        # Fall back to any model
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
