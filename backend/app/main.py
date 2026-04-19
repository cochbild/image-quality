from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import assessments, filesystem, health, images, scans, settings_api
from app.core.auth import require_api_key
from app.core.config import settings
from app.core.logging import get_logger
from app.db.migrations import apply_migrations
from app.db.models import Setting
from app.db.session import SessionLocal, wait_for_database

logger = get_logger("main")


def _seed_default_settings() -> None:
    from app.services.rubric import BORDERLINE_HIGH, BORDERLINE_LOW, DEFAULT_THRESHOLDS

    db = SessionLocal()
    try:
        defaults = {
            "lm_studio_url": settings.LM_STUDIO_URL,
            "lm_studio_model": settings.LM_STUDIO_MODEL,
            "input_dir": settings.IMAGE_INPUT_DIR,
            "output_dir": settings.IMAGE_OUTPUT_DIR,
            "reject_dir": settings.IMAGE_REJECT_DIR,
            "borderline_low": str(BORDERLINE_LOW),
            "borderline_high": str(BORDERLINE_HIGH),
        }
        for cat, val in DEFAULT_THRESHOLDS.items():
            defaults[f"threshold_{cat}"] = str(val)
        for key, value in defaults.items():
            if not db.query(Setting).filter(Setting.key == key).first():
                db.add(Setting(key=key, value=value))
        db.commit()
        logger.info("Default settings seeded")
    except Exception as e:
        logger.error(f"Failed to seed settings: {e}")
        db.rollback()
    finally:
        db.close()


def _register_with_homehub() -> None:
    try:
        resp = httpx.post(
            f"{settings.HOMEHUB_API_URL}/apps/register",
            json={
                "name": "Image Quality Assessor",
                "slug": "image-quality",
                "description": "AI-powered quality assessment for t2i generated images",
                "icon": "\U0001f50d",
                "external_url": settings.IQA_EXTERNAL_URL,
                "dev_url": settings.IQA_EXTERNAL_URL,
                "category": "tools",
                "version": "1.0.0",
                "ports": [
                    {"port": 8100, "protocol": "HTTP", "purpose": "IQA Backend API", "mode": "both"},
                    {"port": 5180, "protocol": "HTTP", "purpose": "IQA Frontend", "mode": "both"},
                ],
            },
            timeout=10.0,
        )
        if resp.status_code in (200, 201):
            data = resp.json()
            api_key = data.get("api_key")
            if api_key:
                db = SessionLocal()
                try:
                    existing = db.query(Setting).filter(Setting.key == "homehub_api_key").first()
                    if existing:
                        existing.value = api_key
                    else:
                        db.add(Setting(key="homehub_api_key", value=api_key))
                    db.commit()
                finally:
                    db.close()
            logger.info("Registered with HomeHub successfully")
        elif resp.status_code == 409:
            logger.info("Already registered with HomeHub")
        else:
            logger.warning(f"HomeHub registration returned {resp.status_code}: {resp.text}")
    except Exception as e:
        logger.warning(f"Could not register with HomeHub (may not be running): {e}")


def _recover_orphaned_scans() -> None:
    """Any scan stuck in `running` from a previous process is now stale."""
    from datetime import datetime, timezone

    from app.db.models.scan import Scan

    db = SessionLocal()
    try:
        stuck = db.query(Scan).filter(Scan.status == "running").all()
        for scan in stuck:
            scan.status = "failed"
            scan.completed_at = datetime.now(timezone.utc)
        if stuck:
            db.commit()
            logger.warning(f"Marked {len(stuck)} orphaned scan(s) as failed on startup")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("Waiting for database connection...")
    wait_for_database()
    apply_migrations()
    _seed_default_settings()
    _recover_orphaned_scans()
    _register_with_homehub()
    yield


app = FastAPI(
    title="Image Quality Assessor API",
    description="AI-powered quality assessment for t2i generated images",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health endpoints remain unauthenticated so container orchestrators can probe them.
app.include_router(health.router, prefix="/api/v1", tags=["health"])

# Every other router sits behind the shared-secret API key dependency.
_protected = [Depends(require_api_key)]
app.include_router(scans.router, prefix="/api/v1/scans", tags=["scans"], dependencies=_protected)
app.include_router(assessments.router, prefix="/api/v1/assessments", tags=["assessments"], dependencies=_protected)
app.include_router(settings_api.router, prefix="/api/v1/settings", tags=["settings"], dependencies=_protected)
app.include_router(images.router, prefix="/api/v1/images", tags=["images"], dependencies=_protected)
app.include_router(filesystem.router, prefix="/api/v1/filesystem", tags=["filesystem"], dependencies=_protected)


@app.get("/")
async def root():
    return {"message": "Image Quality Assessor API", "version": "1.0.0"}
