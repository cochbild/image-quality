from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
from app.db.session import get_db
from app.db.models.scan import Scan
from app.db.models.assessment import Assessment, CategoryScore
from app.db.models.setting import Setting
from app.services.assessment_engine import AssessmentEngine
from app.services.file_manager import list_images, move_image
from app.services.rubric import DEFAULT_THRESHOLDS, BORDERLINE_LOW, BORDERLINE_HIGH, CATEGORIES
from app.core.logging import get_logger

logger = get_logger("scans_api")
router = APIRouter()

# Track active scans
_active_scans: dict[int, bool] = {}  # scan_id -> should_continue


class ScanRequest(BaseModel):
    input_dir: Optional[str] = None
    output_dir: Optional[str] = None
    reject_dir: Optional[str] = None


class ScanResponse(BaseModel):
    id: int
    input_dir: str
    output_dir: str
    reject_dir: str
    started_at: datetime
    completed_at: Optional[datetime]
    total_images: int
    passed_count: int
    failed_count: int
    status: str

    class Config:
        from_attributes = True


def _get_setting(db: Session, key: str, default: str) -> str:
    setting = db.query(Setting).filter(Setting.key == key).first()
    return setting.value if setting else default


def _get_thresholds(db: Session) -> dict[str, int]:
    thresholds = dict(DEFAULT_THRESHOLDS)
    for cat in CATEGORIES:
        val = _get_setting(db, f"threshold_{cat}", str(thresholds[cat]))
        thresholds[cat] = int(val)
    return thresholds


async def _run_scan(scan_id: int, input_dir: str, output_dir: str, reject_dir: str):
    """Background task that runs the actual assessment scan."""
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        images = list_images(input_dir)
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        scan.total_images = len(images)
        db.commit()

        engine = AssessmentEngine()

        lm_url = _get_setting(db, "lm_studio_url", None)
        if lm_url:
            engine.lm_client.base_url = lm_url.rstrip("/")

        model = _get_setting(db, "lm_studio_model", None)
        thresholds = _get_thresholds(db)
        bl_low = int(_get_setting(db, "borderline_low", str(BORDERLINE_LOW)))
        bl_high = int(_get_setting(db, "borderline_high", str(BORDERLINE_HIGH)))

        for image_path in images:
            if not _active_scans.get(scan_id, True):
                scan.status = "cancelled"
                break

            try:
                result = await engine.assess_image(
                    str(image_path),
                    thresholds=thresholds,
                    borderline_low=bl_low,
                    borderline_high=bl_high,
                    model=model,
                )

                # Auto-sort
                if result["passed"]:
                    dest = move_image(str(image_path), output_dir)
                    scan.passed_count += 1
                else:
                    dest = move_image(str(image_path), reject_dir)
                    scan.failed_count += 1

                # Store assessment
                assessment = Assessment(
                    scan_id=scan_id,
                    filename=image_path.name,
                    file_path=str(image_path),
                    destination_path=dest,
                    passed=result["passed"],
                )
                db.add(assessment)
                db.flush()

                for cat, data in result["categories"].items():
                    score = CategoryScore(
                        assessment_id=assessment.id,
                        category=cat,
                        score=data["score"],
                        reasoning=data["reasoning"],
                        was_deep_dive=data["was_deep_dive"],
                    )
                    db.add(score)

                db.commit()
            except Exception as e:
                logger.error(f"Failed to assess {image_path.name}: {e}")
                # Record failed assessment
                assessment = Assessment(
                    scan_id=scan_id,
                    filename=image_path.name,
                    file_path=str(image_path),
                    passed=False,
                )
                db.add(assessment)
                scan.failed_count += 1
                db.commit()

        scan.status = "completed" if scan.status != "cancelled" else "cancelled"
        scan.completed_at = datetime.now(timezone.utc)
        db.commit()

    except Exception as e:
        logger.error(f"Scan {scan_id} failed: {e}")
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if scan:
            scan.status = "failed"
            scan.completed_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        _active_scans.pop(scan_id, None)
        db.close()


@router.post("/", response_model=ScanResponse)
async def start_scan(body: ScanRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    from app.core.config import settings as app_settings

    input_dir = body.input_dir or _get_setting(db, "input_dir", app_settings.IMAGE_INPUT_DIR)
    output_dir = body.output_dir or _get_setting(db, "output_dir", app_settings.IMAGE_OUTPUT_DIR)
    reject_dir = body.reject_dir or _get_setting(db, "reject_dir", app_settings.IMAGE_REJECT_DIR)

    # Validate input dir has images
    try:
        images = list_images(input_dir)
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail=f"Input directory not found: {input_dir}")
    if not images:
        raise HTTPException(status_code=400, detail=f"No images found in: {input_dir}")

    scan = Scan(input_dir=input_dir, output_dir=output_dir, reject_dir=reject_dir, total_images=len(images))
    db.add(scan)
    db.commit()
    db.refresh(scan)

    _active_scans[scan.id] = True
    background_tasks.add_task(_run_scan, scan.id, input_dir, output_dir, reject_dir)

    return scan


@router.get("/", response_model=list[ScanResponse])
async def list_scans(limit: int = 20, db: Session = Depends(get_db)):
    scans = db.query(Scan).order_by(desc(Scan.started_at)).limit(limit).all()
    return scans


@router.get("/{scan_id}", response_model=ScanResponse)
async def get_scan(scan_id: int, db: Session = Depends(get_db)):
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


@router.post("/{scan_id}/cancel")
async def cancel_scan(scan_id: int):
    if scan_id in _active_scans:
        _active_scans[scan_id] = False
        return {"message": "Scan cancellation requested"}
    raise HTTPException(status_code=404, detail="No active scan with that ID")
