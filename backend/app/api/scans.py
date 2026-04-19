from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.config import settings as app_settings
from app.core.logging import get_logger
from app.core.paths import safe_resolve
from app.db.models.assessment import Assessment, CategoryScore
from app.db.models.scan import Scan
from app.db.models.setting import Setting
from app.db.session import get_db
from app.services.assessment_engine import AssessmentEngine
from app.services.file_manager import list_images, move_image
from app.services.rubric import BORDERLINE_HIGH, BORDERLINE_LOW, CATEGORIES, DEFAULT_THRESHOLDS

logger = get_logger("scans_api")
router = APIRouter()


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


def _get_setting(db: Session, key: str, default: str | None) -> str | None:
    setting = db.query(Setting).filter(Setting.key == key).first()
    return setting.value if setting else default


def _get_thresholds(db: Session) -> dict[str, int]:
    thresholds = dict(DEFAULT_THRESHOLDS)
    for cat in CATEGORIES:
        val = _get_setting(db, f"threshold_{cat}", str(thresholds[cat]))
        thresholds[cat] = int(val)
    return thresholds


async def _run_scan(scan_id: int, input_dir: str, output_dir: str, reject_dir: str) -> None:
    """Background task that runs the actual assessment scan.

    Cancellation uses the DB-stored `scan.status == 'cancelling'` sentinel so
    the signal survives process restarts and works across uvicorn workers —
    the earlier in-memory dict only worked when the cancel request happened
    to land on the same worker that was running the scan.
    """
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        images = list_images(input_dir)
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if scan is None:
            return
        scan.total_images = len(images)
        db.commit()

        engine = AssessmentEngine()
        lm_url = _get_setting(db, "lm_studio_url", None)
        if lm_url:
            engine.lm_client.base_url = lm_url.rstrip("/")
        model = _get_setting(db, "lm_studio_model", None)
        thresholds = _get_thresholds(db)
        bl_low = int(_get_setting(db, "borderline_low", str(BORDERLINE_LOW)) or BORDERLINE_LOW)
        bl_high = int(_get_setting(db, "borderline_high", str(BORDERLINE_HIGH)) or BORDERLINE_HIGH)

        cancelled = False
        for image_path in images:
            current_status = db.query(Scan.status).filter(Scan.id == scan_id).scalar()
            if current_status == "cancelling":
                cancelled = True
                break

            try:
                result = await engine.assess_image(
                    str(image_path),
                    thresholds=thresholds,
                    borderline_low=bl_low,
                    borderline_high=bl_high,
                    model=model,
                )

                # Persist the assessment first so scoring survives even if the
                # subsequent file move fails.
                assessment = Assessment(
                    scan_id=scan_id,
                    filename=image_path.name,
                    file_path=str(image_path),
                    destination_path=None,
                    passed=result["passed"],
                )
                db.add(assessment)
                db.flush()
                for cat, data in result["categories"].items():
                    db.add(CategoryScore(
                        assessment_id=assessment.id,
                        category=cat,
                        score=data["score"],
                        reasoning=data["reasoning"],
                        was_deep_dive=data["was_deep_dive"],
                    ))
                if result["passed"]:
                    scan.passed_count += 1
                else:
                    scan.failed_count += 1
                db.commit()

                # Now move the file; on failure the assessment still stands,
                # just without a destination_path.
                target_dir = output_dir if result["passed"] else reject_dir
                try:
                    assessment.destination_path = move_image(str(image_path), target_dir)
                    db.commit()
                except Exception as move_err:
                    logger.error(f"Assessed but failed to move {image_path.name}: {move_err}")
                    db.rollback()

            except Exception as e:
                logger.error(f"Failed to assess {image_path.name}: {e}")
                try:
                    db.rollback()
                except Exception:
                    pass
                # Record a failed assessment so the UI can show the file;
                # best-effort move to reject.
                scan = db.query(Scan).filter(Scan.id == scan_id).first()
                if scan is None:
                    break
                dest: str | None
                try:
                    dest = move_image(str(image_path), reject_dir)
                except Exception as move_err:
                    logger.error(f"Failed to move {image_path.name} to reject: {move_err}")
                    dest = None
                db.add(Assessment(
                    scan_id=scan_id,
                    filename=image_path.name,
                    file_path=str(image_path),
                    destination_path=dest,
                    passed=False,
                ))
                scan.failed_count += 1
                db.commit()

        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if scan:
            scan.status = "cancelled" if cancelled else "completed"
            scan.completed_at = datetime.now(timezone.utc)
            db.commit()

    except Exception as e:
        logger.error(f"Scan {scan_id} failed: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if scan:
            scan.status = "failed"
            scan.completed_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()


@router.post("/", response_model=ScanResponse)
async def start_scan(body: ScanRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    input_raw = body.input_dir or _get_setting(db, "input_dir", app_settings.IMAGE_INPUT_DIR)
    output_raw = body.output_dir or _get_setting(db, "output_dir", app_settings.IMAGE_OUTPUT_DIR)
    reject_raw = body.reject_dir or _get_setting(db, "reject_dir", app_settings.IMAGE_REJECT_DIR)

    roots = app_settings.allowed_image_roots()
    input_resolved = safe_resolve(input_raw, roots)
    output_resolved = safe_resolve(output_raw, roots)
    reject_resolved = safe_resolve(reject_raw, roots)

    if output_resolved == input_resolved:
        raise HTTPException(status_code=400, detail="Output directory must be different from input directory")
    if reject_resolved == input_resolved:
        raise HTTPException(status_code=400, detail="Reject directory must be different from input directory")

    try:
        images = list_images(str(input_resolved))
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail=f"Input directory not found: {input_resolved}")
    if not images:
        raise HTTPException(status_code=400, detail=f"No images found in: {input_resolved}")

    output_resolved.mkdir(parents=True, exist_ok=True)
    reject_resolved.mkdir(parents=True, exist_ok=True)

    input_dir, output_dir, reject_dir = str(input_resolved), str(output_resolved), str(reject_resolved)
    scan = Scan(input_dir=input_dir, output_dir=output_dir, reject_dir=reject_dir, total_images=len(images))
    db.add(scan)
    db.commit()
    db.refresh(scan)

    background_tasks.add_task(_run_scan, scan.id, input_dir, output_dir, reject_dir)
    return scan


@router.get("/", response_model=list[ScanResponse])
async def list_scans(limit: int = 20, db: Session = Depends(get_db)):
    return db.query(Scan).order_by(desc(Scan.started_at)).limit(limit).all()


@router.get("/{scan_id}", response_model=ScanResponse)
async def get_scan(scan_id: int, db: Session = Depends(get_db)):
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


@router.post("/{scan_id}/cancel")
async def cancel_scan(scan_id: int, db: Session = Depends(get_db)):
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    if scan.status not in ("running", "cancelling"):
        raise HTTPException(status_code=400, detail=f"Scan is {scan.status}, cannot cancel")
    scan.status = "cancelling"
    db.commit()
    return {"message": "Scan cancellation requested"}
