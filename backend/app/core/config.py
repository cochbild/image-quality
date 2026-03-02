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
    DATABASE_URL: str = "postgresql://portal_user:portal_pass@localhost:5432/portal_db"
    LM_STUDIO_URL: str = "http://localhost:1234/v1"
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

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
