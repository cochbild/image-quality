from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.core.paths import safe_resolve
from app.db.models.assessment import Assessment
from app.db.session import get_db

router = APIRouter()
logger = get_logger("images")


def _resolved_image_path(assessment: Assessment) -> Path:
    raw = assessment.destination_path or assessment.file_path
    if not raw:
        raise HTTPException(status_code=404, detail="Image path not recorded")
    resolved = safe_resolve(raw, settings.allowed_image_roots())
    if not resolved.is_file():
        raise HTTPException(status_code=404, detail="Image file not found")
    return resolved


def _thumbnail_path(assessment_id: int) -> Path:
    return Path(settings.IMAGE_THUMBS_DIR) / f"{assessment_id}.jpg"


def _generate_thumbnail(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with Image.open(source) as img:
            img = img.convert("RGB")
            img.thumbnail(
                (settings.THUMBNAIL_MAX_EDGE, settings.THUMBNAIL_MAX_EDGE),
                Image.Resampling.LANCZOS,
            )
            img.save(destination, format="JPEG", quality=80, optimize=True)
    except (UnidentifiedImageError, OSError) as exc:
        logger.warning(f"Thumbnail generation failed for {source}: {exc}")
        raise HTTPException(status_code=415, detail="Image could not be processed") from exc


@router.get("/{assessment_id}")
async def get_image(assessment_id: int, db: Session = Depends(get_db)):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return FileResponse(_resolved_image_path(assessment))


@router.get("/{assessment_id}/thumbnail")
async def get_thumbnail(assessment_id: int, db: Session = Depends(get_db)):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    cache_path = _thumbnail_path(assessment_id)
    if not cache_path.is_file():
        source = _resolved_image_path(assessment)
        _generate_thumbnail(source, cache_path)

    return FileResponse(cache_path, media_type="image/jpeg")
