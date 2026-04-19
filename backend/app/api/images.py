from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.paths import safe_resolve
from app.db.models.assessment import Assessment
from app.db.session import get_db

router = APIRouter()


def _resolved_image_path(assessment: Assessment) -> Path:
    raw = assessment.destination_path or assessment.file_path
    if not raw:
        raise HTTPException(status_code=404, detail="Image path not recorded")
    resolved = safe_resolve(raw, settings.allowed_image_roots())
    if not resolved.is_file():
        raise HTTPException(status_code=404, detail="Image file not found")
    return resolved


@router.get("/{assessment_id}")
async def get_image(assessment_id: int, db: Session = Depends(get_db)):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return FileResponse(_resolved_image_path(assessment))


@router.get("/{assessment_id}/thumbnail")
async def get_thumbnail(assessment_id: int, db: Session = Depends(get_db)):
    # Full image for now; a real thumbnail pipeline can replace this later.
    return await get_image(assessment_id, db)
