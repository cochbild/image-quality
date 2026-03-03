import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.api import scans, assessments, settings_api, health, images, filesystem
from app.db.session import engine, wait_for_database, SessionLocal
from app.db.base import Base
from app.db.models import Scan, Assessment, CategoryScore, Setting
from app.core.logging import get_logger

logger = get_logger("main")

# Wait for database
logger.info("Waiting for database connection...")
wait_for_database()

# Create IQA tables
logger.info("Creating IQA database tables...")
Base.metadata.create_all(bind=engine)
logger.info("IQA database tables created")

app = FastAPI(
    title="Image Quality Assessor API",
    description="AI-powered quality assessment for t2i generated images",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(scans.router, prefix="/api/v1/scans", tags=["scans"])
app.include_router(assessments.router, prefix="/api/v1/assessments", tags=["assessments"])
app.include_router(settings_api.router, prefix="/api/v1/settings", tags=["settings"])
app.include_router(images.router, prefix="/api/v1/images", tags=["images"])
app.include_router(filesystem.router, prefix="/api/v1/filesystem", tags=["filesystem"])

# Mount images directory for serving thumbnails
app.mount("/images", StaticFiles(directory=settings.IMAGE_OUTPUT_DIR, check_dir=False), name="output_images")
app.mount("/rejects", StaticFiles(directory=settings.IMAGE_REJECT_DIR, check_dir=False), name="reject_images")


def seed_default_settings():
    """Seed default settings on first startup."""
    from app.services.rubric import DEFAULT_THRESHOLDS, BORDERLINE_LOW, BORDERLINE_HIGH
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
            existing = db.query(Setting).filter(Setting.key == key).first()
            if not existing:
                db.add(Setting(key=key, value=value))
        db.commit()
        logger.info("Default settings seeded")
    except Exception as e:
        logger.error(f"Failed to seed settings: {e}")
        db.rollback()
    finally:
        db.close()


def register_with_homehub():
    """Self-register with HomeHub portal on startup."""
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


seed_default_settings()
register_with_homehub()


@app.get("/")
async def root():
    return {"message": "Image Quality Assessor API", "version": "1.0.0"}
