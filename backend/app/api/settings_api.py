from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.config import settings as app_settings
from app.core.paths import safe_resolve
from app.core.url_validator import validate_outbound_url
from app.db.models.setting import Setting
from app.db.session import get_db
from app.services.rubric import CATEGORIES

router = APIRouter()

# Settings that clients are allowed to read AND overwrite.
# Anything outside this set (notably `homehub_api_key`) is either internal state
# or a footgun and must not be writable through the public API.
_WRITABLE_KEYS = {
    "lm_studio_url",
    "lm_studio_model",
    "input_dir",
    "output_dir",
    "reject_dir",
    "borderline_low",
    "borderline_high",
}
_WRITABLE_KEYS.update(f"threshold_{cat}" for cat in CATEGORIES)

# URL-typed settings whose values must pass the outbound-URL validator.
_URL_KEYS = {"lm_studio_url"}

# Path-typed settings that must remain inside the env-defined image roots.
_PATH_KEYS = {"input_dir", "output_dir", "reject_dir"}


class SettingUpdate(BaseModel):
    value: str


@router.get("/")
async def get_all_settings(db: Session = Depends(get_db)):
    # `homehub_api_key` is stored server-side only — never return it.
    settings_rows = db.query(Setting).filter(Setting.key != "homehub_api_key").all()
    return {s.key: s.value for s in settings_rows}


@router.get("/{key}")
async def get_setting(key: str, db: Session = Depends(get_db)):
    if key == "homehub_api_key":
        raise HTTPException(status_code=404, detail="Setting not found")
    setting = db.query(Setting).filter(Setting.key == key).first()
    if not setting:
        return {"key": key, "value": None}
    return {"key": setting.key, "value": setting.value}


@router.put("/{key}")
async def upsert_setting(key: str, body: SettingUpdate, db: Session = Depends(get_db)):
    if key not in _WRITABLE_KEYS:
        raise HTTPException(status_code=400, detail=f"Setting '{key}' is not writable")
    if key in _URL_KEYS:
        validate_outbound_url(body.value)
    if key in _PATH_KEYS:
        safe_resolve(body.value, app_settings.allowed_image_roots())

    setting = db.query(Setting).filter(Setting.key == key).first()
    if setting:
        setting.value = body.value
    else:
        setting = Setting(key=key, value=body.value)
        db.add(setting)
    db.commit()
    db.refresh(setting)
    return {"key": setting.key, "value": setting.value}
