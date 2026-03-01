from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.db.session import get_db
from app.db.models.assessment import Assessment, CategoryScore

router = APIRouter()


class CategoryScoreResponse(BaseModel):
    category: str
    score: int
    reasoning: Optional[str]
    was_deep_dive: bool

    class Config:
        from_attributes = True


class AssessmentResponse(BaseModel):
    id: int
    scan_id: int
    filename: str
    file_path: str
    destination_path: Optional[str]
    passed: Optional[bool]
    triage_score: Optional[float]
    created_at: datetime
    category_scores: list[CategoryScoreResponse]

    class Config:
        from_attributes = True


@router.get("/by-scan/{scan_id}", response_model=list[AssessmentResponse])
async def get_assessments_by_scan(
    scan_id: int,
    passed: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Assessment).options(joinedload(Assessment.category_scores)).filter(Assessment.scan_id == scan_id)
    if passed is not None:
        query = query.filter(Assessment.passed == passed)
    return query.order_by(Assessment.created_at).all()


@router.get("/stats/summary")
async def get_stats(db: Session = Depends(get_db)):
    total = db.query(Assessment).count()
    passed = db.query(Assessment).filter(Assessment.passed == True).count()
    failed = db.query(Assessment).filter(Assessment.passed == False).count()
    return {
        "total_assessed": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": round(passed / total * 100, 1) if total > 0 else 0,
    }


@router.get("/{assessment_id}", response_model=AssessmentResponse)
async def get_assessment(assessment_id: int, db: Session = Depends(get_db)):
    assessment = (
        db.query(Assessment)
        .options(joinedload(Assessment.category_scores))
        .filter(Assessment.id == assessment_id)
        .first()
    )
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return assessment
