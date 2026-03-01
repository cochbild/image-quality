from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
from app.db.session import get_db
from app.db.models.assessment import Assessment

router = APIRouter()


@router.get("/{assessment_id}")
async def get_image(assessment_id: int, db: Session = Depends(get_db)):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    path = assessment.destination_path or assessment.file_path
    if not Path(path).exists():
        raise HTTPException(status_code=404, detail="Image file not found")

    return FileResponse(path)


@router.get("/{assessment_id}/thumbnail")
async def get_thumbnail(assessment_id: int, db: Session = Depends(get_db)):
    # For now, serve the full image. Thumbnail generation can be added later.
    return await get_image(assessment_id, db)
