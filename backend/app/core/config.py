import os
import sys
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List


def _default_data_dir() -> Path:
    """Use a sensible default data directory based on platform."""
    if sys.platform == "win32":
        base = Path(os.environ.get("USERPROFILE", "C:\\Users\\Public"))
        return base / "Pictures" / "IQA"
    return Path("/app/images")


_DATA = _default_data_dir()


class Settings(BaseSettings):
    IQA_API_KEY: str
    DATABASE_URL: str
    LM_STUDIO_URL: str = "http://localhost:1234/v1"
    LM_STUDIO_MODEL: str = "qwen/qwen3-vl-8b"
    HOMEHUB_API_URL: str = "http://localhost:8000/api/v1"
    IQA_EXTERNAL_URL: str = "http://localhost:5180"
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: List[str] = [
        "http://localhost:5180",
        "http://localhost:8100",
    ]
    IMAGE_INPUT_DIR: str = str(_DATA / "input")
    IMAGE_OUTPUT_DIR: str = str(_DATA / "output")
    IMAGE_REJECT_DIR: str = str(_DATA / "reject")
    IMAGE_THUMBS_DIR: str = str(_DATA / "thumbs")
    THUMBNAIL_MAX_EDGE: int = 256
    LOG_LEVEL: str = "INFO"

    @field_validator('CORS_ORIGINS', mode='after')
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, list):
            return v
        try:
            import json
            parsed = json.loads(v)
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass
        return [origin.strip() for origin in v.split(',') if origin.strip()]

    @field_validator('IQA_API_KEY', mode='after')
    @classmethod
    def require_non_empty_api_key(cls, v: str) -> str:
        if not v or len(v) < 16:
            raise ValueError(
                "IQA_API_KEY must be set to a non-empty string of at least 16 characters. "
                "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
        return v

    def allowed_image_roots(self) -> list[str]:
        """Roots that bound every filesystem operation the API will perform."""
        return [self.IMAGE_INPUT_DIR, self.IMAGE_OUTPUT_DIR, self.IMAGE_REJECT_DIR]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
