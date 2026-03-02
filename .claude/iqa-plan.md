# Image Quality Assessor - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a web application that uses Qwen VL models via LM Studio to assess t2i image quality with a 6-category rubric, hybrid triage, and auto-sort.

**Architecture:** FastAPI backend serves a React+MUI frontend. The backend connects to LM Studio's OpenAI-compatible API to analyze images, stores results in shared PostgreSQL (HomeHub's portal_db), and auto-sorts images into pass/reject directories. Self-registers with HomeHub on startup.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.0, Pydantic v2, React 18, TypeScript, Vite, MUI v7, Axios, Docker, PostgreSQL 15

**Design doc:** `docs/plans/2026-02-28-image-quality-assessor-design.md`

**HomeHub reference:** `C:\Users\dalec\source\repos\HomeHub` (match patterns from this project)

---

## Task 1: Project Scaffolding — Backend

**Files:**
- Create: `backend/app/__init__.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/config.py`
- Create: `backend/app/core/logging.py`
- Create: `backend/app/db/__init__.py`
- Create: `backend/app/db/base.py`
- Create: `backend/app/db/session.py`
- Create: `backend/app/db/models/__init__.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/services/__init__.py`
- Create: `backend/requirements.txt`
- Create: `backend/Dockerfile`

**Step 1: Create requirements.txt**

```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-multipart>=0.0.6
httpx>=0.25.0
aiofiles>=23.0.0
```

**Step 2: Create config.py**

Follow HomeHub's `portal-backend/app/core/config.py` pattern exactly:

```python
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://portal_user:portal_pass@portal-postgres:5432/portal_db"
    LM_STUDIO_URL: str = "http://host.docker.internal:1234/v1"
    HOMEHUB_API_URL: str = "http://portal-backend:8000/api/v1"
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: List[str] = [
        "http://localhost:5174",
        "http://localhost:8100",
    ]
    IMAGE_INPUT_DIR: str = "/app/images/input"
    IMAGE_OUTPUT_DIR: str = "/app/images/output"
    IMAGE_REJECT_DIR: str = "/app/images/reject"
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
```

**Step 3: Create logging.py**

```python
import logging

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(f"iqa.{name}")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
```

**Step 4: Create db/base.py**

```python
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
```

**Step 5: Create db/session.py**

Match HomeHub's `portal-backend/app/db/session.py` pattern — engine with pool_pre_ping, SessionLocal, wait_for_database(), get_db() dependency.

**Step 6: Create all __init__.py files** (empty)

**Step 7: Create Dockerfile**

Match HomeHub's `portal-backend/Dockerfile` pattern:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y gcc postgresql-client && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p /app/images/input /app/images/output /app/images/reject && chmod 755 /app/images
EXPOSE 8100
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8100"]
```

**Step 8: Commit**

```bash
git add backend/
git commit -m "feat: scaffold backend with config, db session, and Dockerfile"
```

---

## Task 2: Database Models

**Files:**
- Create: `backend/app/db/models/scan.py`
- Create: `backend/app/db/models/assessment.py`
- Create: `backend/app/db/models/setting.py`

**Step 1: Create scan.py**

```python
from sqlalchemy import Column, Integer, String, DateTime, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base

class Scan(Base):
    __tablename__ = "iqa_scans"

    id = Column(Integer, primary_key=True, index=True)
    input_dir = Column(String, nullable=False)
    output_dir = Column(String, nullable=False)
    reject_dir = Column(String, nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    total_images = Column(Integer, nullable=False, default=0)
    passed_count = Column(Integer, nullable=False, default=0)
    failed_count = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default="running")

    assessments = relationship("Assessment", back_populates="scan", cascade="all, delete-orphan")
```

**Step 2: Create assessment.py**

```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base

class Assessment(Base):
    __tablename__ = "iqa_assessments"

    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("iqa_scans.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    destination_path = Column(String, nullable=True)
    passed = Column(Boolean, nullable=True)
    triage_score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    scan = relationship("Scan", back_populates="assessments")
    category_scores = relationship("CategoryScore", back_populates="assessment", cascade="all, delete-orphan")

class CategoryScore(Base):
    __tablename__ = "iqa_category_scores"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("iqa_assessments.id", ondelete="CASCADE"), nullable=False)
    category = Column(String(30), nullable=False)
    score = Column(Integer, nullable=False)
    reasoning = Column(Text, nullable=True)
    was_deep_dive = Column(Boolean, nullable=False, default=False)

    assessment = relationship("Assessment", back_populates="category_scores")

    __table_args__ = (
        CheckConstraint('score >= 1 AND score <= 10', name='ck_score_range'),
    )
```

**Step 3: Create setting.py**

```python
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.db.base import Base

class Setting(Base):
    __tablename__ = "iqa_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

**Step 4: Update models/__init__.py**

```python
from app.db.models.scan import Scan
from app.db.models.assessment import Assessment, CategoryScore
from app.db.models.setting import Setting
```

**Step 5: Commit**

```bash
git add backend/app/db/models/
git commit -m "feat: add SQLAlchemy models for scans, assessments, and settings"
```

---

## Task 3: LM Studio Client & Rubric Prompts

**Files:**
- Create: `backend/app/services/lm_studio_client.py`
- Create: `backend/app/services/rubric.py`

**Step 1: Create lm_studio_client.py**

This is the core integration with LM Studio's OpenAI-compatible API. It sends images as base64-encoded content in the vision message format.

```python
import base64
import httpx
from pathlib import Path
from typing import Optional
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("lm_studio")

class LMStudioClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.LM_STUDIO_URL).rstrip("/")

    async def list_models(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.base_url}/models")
            resp.raise_for_status()
            return resp.json().get("data", [])

    async def analyze_image(self, image_path: str, prompt: str, model: Optional[str] = None) -> str:
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        suffix = path.suffix.lower().lstrip(".")
        mime_map = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp", "gif": "gif"}
        mime_type = f"image/{mime_map.get(suffix, suffix)}"

        image_data = base64.b64encode(path.read_bytes()).decode("utf-8")

        # Resolve model: parameter > DB setting > first available
        if not model:
            model = await self._get_default_model()

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_data}"}},
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
            "max_tokens": 2048,
            "temperature": 0.1,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{self.base_url}/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def _get_default_model(self) -> str:
        models = await self.list_models()
        if not models:
            raise RuntimeError("No models loaded in LM Studio")
        return models[0]["id"]

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/models")
                return resp.status_code == 200
        except Exception:
            return False
```

**Step 2: Create rubric.py**

This contains the triage prompt and the 6 category-specific deep-dive prompts. These are the expert rubric prompts derived from t2i artifact research.

```python
CATEGORIES = ["anatomical", "compositional", "physics", "texture", "technical", "semantic"]

DEFAULT_THRESHOLDS = {
    "anatomical": 7,
    "compositional": 6,
    "physics": 6,
    "texture": 5,
    "technical": 5,
    "semantic": 6,
}

BORDERLINE_LOW = 4
BORDERLINE_HIGH = 8

TRIAGE_PROMPT = """You are an expert image quality assessor specializing in AI-generated (text-to-image) artwork. Analyze this image for common t2i defects.

Score each category from 1 (worst) to 10 (best). Be strict and precise.

Categories:
1. ANATOMICAL - Human body accuracy: correct finger count (5 per hand), face symmetry, proper limb count, no merged bodies, correct joint articulation, proper feet/toes
2. COMPOSITIONAL - Scene structure: object scale consistency, perspective coherence, no floating objects, no object merging/fusion
3. PHYSICS - Physical plausibility: shadow direction consistency, shadow presence, reflection accuracy, depth-of-field consistency, gravity logic
4. TEXTURE - Surface quality: skin realism (not waxy/plastic), hair quality, fabric integrity, material consistency, no edge bleeding
5. TECHNICAL - Rendering quality: no noise artifacts, no color banding, consistent resolution, no tiling/repeating patterns, clean edges
6. SEMANTIC - Logical consistency: text readability (if present), correct object counts, contextually appropriate combinations, logical spatial relationships

If NO humans are present in the image, score ANATOMICAL as 10.

Respond ONLY with valid JSON in this exact format, no other text:
{
  "anatomical": {"score": <1-10>, "reasoning": "<brief explanation>"},
  "compositional": {"score": <1-10>, "reasoning": "<brief explanation>"},
  "physics": {"score": <1-10>, "reasoning": "<brief explanation>"},
  "texture": {"score": <1-10>, "reasoning": "<brief explanation>"},
  "technical": {"score": <1-10>, "reasoning": "<brief explanation>"},
  "semantic": {"score": <1-10>, "reasoning": "<brief explanation>"}
}"""

DEEP_DIVE_PROMPTS = {
    "anatomical": """You are an expert anatomist reviewing an AI-generated image for human body defects. Examine EVERY detail carefully.

Check systematically:
HANDS: Count fingers on each visible hand. Are there exactly 5? Check thumb placement (correct side?). Check finger proportions, joint bending direction, nail placement. Are any fingers fused or merged?
FACE: Are eyes symmetric and at the same height? Correct pupil shapes? Mouth/teeth intact? Ears present and correctly placed? Nose bridge intact? Skin texture natural (not waxy)?
BODY: Count all limbs. Are any bodies merged together? Do all joints bend in anatomically possible directions? Are proportions correct (head-to-body ratio, arm length vs torso, etc.)?
FEET: If visible, correct toe count? No fused feet? Proper orientation?

If NO humans are present, score 10.

Score 1-10 where:
- 10: Flawless anatomy
- 7-9: Minor imperfections (slight asymmetry, minor proportion issues)
- 4-6: Noticeable defects (extra/missing finger, mild face distortion)
- 1-3: Severe deformations (merged bodies, extra limbs, melted features)

Respond ONLY with valid JSON:
{"score": <1-10>, "reasoning": "<detailed explanation of findings>"}""",

    "compositional": """You are an expert compositor reviewing an AI-generated image for structural defects.

Check systematically:
SCALE: Are all objects at correct relative sizes? No impossible scale relationships?
PERSPECTIVE: Is there a consistent vanishing point? Do lines converge correctly?
SPATIAL: Are objects properly grounded? Anything floating without support? Any objects impossibly merged or overlapping?
FOREGROUND/BACKGROUND: Consistent relationship? No jarring transitions?

Score 1-10 where:
- 10: Flawless composition
- 7-9: Minor inconsistencies
- 4-6: Noticeable errors (wrong scale, perspective breaks)
- 1-3: Major structural failures

Respond ONLY with valid JSON:
{"score": <1-10>, "reasoning": "<detailed explanation of findings>"}""",

    "physics": """You are a physics expert reviewing an AI-generated image for physical plausibility.

Check systematically:
SHADOWS: Do all shadows point in a consistent direction? Does every grounded object cast a shadow? Are shadow lengths proportional?
REFLECTIONS: Are reflections in mirrors/water/glass accurate? Do they match the objects they reflect?
LIGHTING: Is the light source consistent? Do highlights and shadows agree on light direction?
DEPTH OF FIELD: Is blur consistent with a single focal plane? No randomly sharp/blurry regions?
GRAVITY: Are structures properly supported? Do liquids behave correctly?

Score 1-10 where:
- 10: Physically plausible scene
- 7-9: Minor inconsistencies
- 4-6: Noticeable violations (wrong shadow direction, missing reflections)
- 1-3: Major physics failures

Respond ONLY with valid JSON:
{"score": <1-10>, "reasoning": "<detailed explanation of findings>"}""",

    "texture": """You are a texture and materials expert reviewing an AI-generated image for surface quality.

Check systematically:
SKIN: Does skin look natural? Has pores, fine wrinkles, subtle color variation? Or is it waxy, plastic, overly smooth?
HAIR: Natural variation in strands? Proper physics? Not merging with background? Natural hairline?
FABRIC: Correct fold patterns? No impossible pattern warping? Functional clothing design? No texture bleeding?
MATERIALS: Do metals look metallic? Glass translucent? Wood grainy? Consistent material properties across each surface?
EDGES: Clean boundaries between different materials? No color/texture bleeding between objects?

Score 1-10 where:
- 10: Photorealistic textures
- 7-9: Minor quality issues
- 4-6: Noticeable artifacts (waxy skin, uniform hair, pattern warping)
- 1-3: Severe texture failures

Respond ONLY with valid JSON:
{"score": <1-10>, "reasoning": "<detailed explanation of findings>"}""",

    "technical": """You are a technical image quality expert reviewing an AI-generated image for rendering artifacts.

Check systematically:
NOISE: Any visible noise patches? Residual denoising artifacts? Grain inconsistencies?
BANDING: Color banding in gradients or smooth areas? Visible gradient steps?
RESOLUTION: Consistent sharpness across the image? No regions at different quality levels?
PATTERNS: Any tiling or repeating artifacts? Watermark-like ghost patterns? Grid structures?
EDGES: Clean edges on all objects? No halos, aliasing, or moire patterns? No edge bleeding?

Score 1-10 where:
- 10: Technically flawless
- 7-9: Minor artifacts
- 4-6: Noticeable technical issues (banding, noise patches, resolution inconsistency)
- 1-3: Severe rendering failures

Respond ONLY with valid JSON:
{"score": <1-10>, "reasoning": "<detailed explanation of findings>"}""",

    "semantic": """You are a semantic consistency expert reviewing an AI-generated image for logical coherence.

Check systematically:
TEXT: If any text is visible, is it readable? Correctly spelled? In the right language? Or garbled/distorted?
COUNTING: Do object counts match what the scene implies? No duplicate objects that shouldn't exist? No missing expected objects?
CONTEXT: Are object combinations contextually appropriate? No anachronisms? No culturally impossible scenarios?
SPATIAL LOGIC: Do spatial relationships make sense? Are objects in expected positions relative to each other?
OBJECT INTEGRITY: Are all objects complete? No hybrid/contradictory states? No missing expected components (e.g., car without wheels)?

Score 1-10 where:
- 10: Semantically flawless
- 7-9: Minor inconsistencies
- 4-6: Noticeable logical errors (garbled text, wrong object count)
- 1-3: Major semantic failures

Respond ONLY with valid JSON:
{"score": <1-10>, "reasoning": "<detailed explanation of findings>"}""",
}
```

**Step 3: Commit**

```bash
git add backend/app/services/
git commit -m "feat: add LM Studio client and expert rubric prompts for 6-category assessment"
```

---

## Task 4: Assessment Engine (Hybrid Triage)

**Files:**
- Create: `backend/app/services/assessment_engine.py`
- Create: `backend/app/services/file_manager.py`

**Step 1: Create file_manager.py**

Handles scanning directories for images and moving files to pass/reject dirs.

```python
import shutil
from pathlib import Path
from app.core.logging import get_logger

logger = get_logger("file_manager")

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff"}

def list_images(directory: str) -> list[Path]:
    dir_path = Path(directory)
    if not dir_path.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")
    images = [f for f in dir_path.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS]
    return sorted(images, key=lambda p: p.name)

def move_image(src: str, dest_dir: str) -> str:
    src_path = Path(src)
    dest_dir_path = Path(dest_dir)
    dest_dir_path.mkdir(parents=True, exist_ok=True)

    dest_path = dest_dir_path / src_path.name

    # Handle filename collisions
    if dest_path.exists():
        stem = src_path.stem
        suffix = src_path.suffix
        counter = 1
        while dest_path.exists():
            dest_path = dest_dir_path / f"{stem}_{counter}{suffix}"
            counter += 1

    shutil.move(str(src_path), str(dest_path))
    logger.info(f"Moved {src_path.name} -> {dest_path}")
    return str(dest_path)
```

**Step 2: Create assessment_engine.py**

The core hybrid triage engine. Performs triage pass, then deep-dives on borderline categories.

```python
import json
import re
from typing import Optional
from app.services.lm_studio_client import LMStudioClient
from app.services.rubric import (
    TRIAGE_PROMPT, DEEP_DIVE_PROMPTS, CATEGORIES,
    DEFAULT_THRESHOLDS, BORDERLINE_LOW, BORDERLINE_HIGH,
)
from app.core.logging import get_logger

logger = get_logger("assessment")

def parse_json_response(text: str) -> dict:
    """Extract JSON from model response, handling markdown code blocks."""
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try extracting from markdown code block
    match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    # Try finding first { to last }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass
    raise ValueError(f"Could not parse JSON from response: {text[:200]}")


class AssessmentEngine:
    def __init__(self, lm_client: Optional[LMStudioClient] = None):
        self.lm_client = lm_client or LMStudioClient()

    async def assess_image(
        self,
        image_path: str,
        thresholds: Optional[dict[str, int]] = None,
        borderline_low: int = BORDERLINE_LOW,
        borderline_high: int = BORDERLINE_HIGH,
        model: Optional[str] = None,
    ) -> dict:
        """Run hybrid triage assessment on a single image.

        Returns:
            {
                "passed": bool,
                "categories": {
                    "anatomical": {"score": int, "reasoning": str, "was_deep_dive": bool},
                    ...
                }
            }
        """
        thresholds = thresholds or DEFAULT_THRESHOLDS

        # Phase 1: Triage pass
        logger.info(f"Triage pass: {image_path}")
        triage_response = await self.lm_client.analyze_image(image_path, TRIAGE_PROMPT, model=model)
        triage_result = parse_json_response(triage_response)

        categories = {}
        for cat in CATEGORIES:
            cat_data = triage_result.get(cat, {})
            score = int(cat_data.get("score", 1))
            reasoning = cat_data.get("reasoning", "")
            categories[cat] = {"score": score, "reasoning": reasoning, "was_deep_dive": False}

        # Phase 2: Deep dive on borderline categories
        borderline_cats = [
            cat for cat, data in categories.items()
            if borderline_low <= data["score"] <= borderline_high
        ]

        if borderline_cats:
            logger.info(f"Deep dive on borderline categories: {borderline_cats}")
            for cat in borderline_cats:
                prompt = DEEP_DIVE_PROMPTS[cat]
                deep_response = await self.lm_client.analyze_image(image_path, prompt, model=model)
                deep_result = parse_json_response(deep_response)
                categories[cat] = {
                    "score": int(deep_result.get("score", categories[cat]["score"])),
                    "reasoning": deep_result.get("reasoning", categories[cat]["reasoning"]),
                    "was_deep_dive": True,
                }

        # Determine pass/fail
        passed = all(
            categories[cat]["score"] >= thresholds.get(cat, DEFAULT_THRESHOLDS[cat])
            for cat in CATEGORIES
        )

        return {"passed": passed, "categories": categories}
```

**Step 3: Commit**

```bash
git add backend/app/services/
git commit -m "feat: add hybrid triage assessment engine and file manager"
```

---

## Task 5: Backend API Routes

**Files:**
- Create: `backend/app/api/scans.py`
- Create: `backend/app/api/assessments.py`
- Create: `backend/app/api/settings_api.py`
- Create: `backend/app/api/health.py`
- Create: `backend/app/main.py`

**Step 1: Create health.py**

```python
from fastapi import APIRouter
from app.services.lm_studio_client import LMStudioClient

router = APIRouter()

@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "iqa-backend"}

@router.get("/lm-studio/status")
async def lm_studio_status():
    client = LMStudioClient()
    healthy = await client.health_check()
    return {"connected": healthy, "url": client.base_url}

@router.get("/lm-studio/models")
async def lm_studio_models():
    client = LMStudioClient()
    try:
        models = await client.list_models()
        return {"models": models}
    except Exception as e:
        return {"models": [], "error": str(e)}
```

**Step 2: Create settings_api.py**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.db.session import get_db
from app.db.models.setting import Setting

router = APIRouter()

class SettingUpdate(BaseModel):
    value: str

class SettingResponse(BaseModel):
    key: str
    value: str

    class Config:
        from_attributes = True

@router.get("/")
async def get_all_settings(db: Session = Depends(get_db)):
    settings = db.query(Setting).all()
    return {s.key: s.value for s in settings}

@router.get("/{key}")
async def get_setting(key: str, db: Session = Depends(get_db)):
    setting = db.query(Setting).filter(Setting.key == key).first()
    if not setting:
        return {"key": key, "value": None}
    return {"key": setting.key, "value": setting.value}

@router.put("/{key}")
async def upsert_setting(key: str, body: SettingUpdate, db: Session = Depends(get_db)):
    setting = db.query(Setting).filter(Setting.key == key).first()
    if setting:
        setting.value = body.value
    else:
        setting = Setting(key=key, value=body.value)
        db.add(setting)
    db.commit()
    db.refresh(setting)
    return {"key": setting.key, "value": setting.value}
```

**Step 3: Create scans.py**

This is the main endpoint that orchestrates a full scan. It creates a scan record, iterates over images in the input directory, runs assessments, stores results, and auto-sorts.

```python
import asyncio
import json
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
```

**Step 4: Create assessments.py**

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
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
```

**Step 5: Create main.py**

```python
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.api import scans, assessments, settings_api, health
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

app.include_router(health.router, tags=["health"])
app.include_router(scans.router, prefix="/api/v1/scans", tags=["scans"])
app.include_router(assessments.router, prefix="/api/v1/assessments", tags=["assessments"])
app.include_router(settings_api.router, prefix="/api/v1/settings", tags=["settings"])

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
            "lm_studio_model": "",
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
                "external_url": "http://localhost:5174",
                "dev_url": "http://localhost:5174",
                "app_type": "external",
                "category": "tools",
                "is_visible": True,
                "ports": [
                    {"port": 8100, "protocol": "HTTP", "purpose": "IQA Backend API", "mode": "both"},
                    {"port": 5174, "protocol": "HTTP", "purpose": "IQA Frontend (dev)", "mode": "development"},
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
```

**Step 6: Commit**

```bash
git add backend/app/api/ backend/app/main.py
git commit -m "feat: add API routes for scans, assessments, settings, and HomeHub registration"
```

---

## Task 6: Project Scaffolding — Frontend

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/theme.ts`
- Create: `frontend/src/vite-env.d.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/Dockerfile`
- Create: `frontend/nginx.conf`

**Step 1: Create package.json**

Match HomeHub's dependencies:

```json
{
  "name": "iqa-frontend",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "@emotion/react": "^11.14.0",
    "@emotion/styled": "^11.14.1",
    "@mui/icons-material": "^7.3.8",
    "@mui/material": "^7.3.8",
    "axios": "^1.6.2",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.43",
    "@types/react-dom": "^18.2.17",
    "@vitejs/plugin-react": "^4.2.1",
    "typescript": "^5.2.2",
    "vite": "^5.0.8"
  }
}
```

**Step 2: Create vite.config.ts**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/',
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
  },
  server: {
    port: 5174,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://localhost:8100',
        changeOrigin: true,
      },
      '/images': {
        target: 'http://localhost:8100',
        changeOrigin: true,
      },
      '/rejects': {
        target: 'http://localhost:8100',
        changeOrigin: true,
      },
    },
  },
})
```

**Step 3: Create theme.ts**

Copy HomeHub's theme exactly:

```typescript
import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
    background: {
      default: '#f5f5f5',
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 12,
        },
      },
    },
  },
});

export default theme;
```

**Step 4: Create api/client.ts**

Simpler than HomeHub's — no auth needed for this app:

```typescript
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

export default apiClient;
```

**Step 5: Create index.html**

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap" rel="stylesheet" />
    <title>Image Quality Assessor</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

**Step 6: Create main.tsx**

```typescript
import React from 'react'
import ReactDOM from 'react-dom/client'
import { ThemeProvider } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'
import theme from './theme'
import App from './App'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <App />
    </ThemeProvider>
  </React.StrictMode>,
)
```

**Step 7: Create App.tsx**

```typescript
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import ScanView from './pages/ScanView';
import ImageDetail from './pages/ImageDetail';
import History from './pages/History';
import Settings from './pages/Settings';
import NavBar from './components/NavBar';

export default function App() {
  return (
    <BrowserRouter>
      <NavBar />
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/scan" element={<ScanView />} />
        <Route path="/scan/:scanId" element={<ScanView />} />
        <Route path="/assessment/:id" element={<ImageDetail />} />
        <Route path="/history" element={<History />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </BrowserRouter>
  );
}
```

**Step 8: Create tsconfig.json, tsconfig.node.json, vite-env.d.ts**

Standard Vite+React+TS configs.

**Step 9: Create Dockerfile and nginx.conf**

Match HomeHub's frontend Dockerfile exactly:

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

nginx.conf:
```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://iqa-backend:8100;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /images/ {
        proxy_pass http://iqa-backend:8100;
    }

    location /rejects/ {
        proxy_pass http://iqa-backend:8100;
    }
}
```

**Step 10: Run npm install**

```bash
cd frontend && npm install
```

**Step 11: Commit**

```bash
git add frontend/
git commit -m "feat: scaffold frontend with React, MUI, Vite, and HomeHub-matching theme"
```

---

## Task 7: Frontend — NavBar & API Functions

**Files:**
- Create: `frontend/src/components/NavBar.tsx`
- Create: `frontend/src/api/scans.ts`
- Create: `frontend/src/api/assessments.ts`
- Create: `frontend/src/api/settings.ts`

**Step 1: Create NavBar.tsx**

```typescript
import { AppBar, Toolbar, Typography, Button, Box } from '@mui/material';
import { useNavigate, useLocation } from 'react-router-dom';

export default function NavBar() {
  const navigate = useNavigate();
  const location = useLocation();

  const navItems = [
    { label: 'Dashboard', path: '/' },
    { label: 'New Scan', path: '/scan' },
    { label: 'History', path: '/history' },
    { label: 'Settings', path: '/settings' },
  ];

  return (
    <AppBar position="sticky">
      <Toolbar>
        <Typography variant="h6" sx={{ mr: 4, cursor: 'pointer' }} onClick={() => navigate('/')}>
          IQA
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          {navItems.map((item) => (
            <Button
              key={item.path}
              color="inherit"
              onClick={() => navigate(item.path)}
              sx={{
                fontWeight: location.pathname === item.path ? 700 : 400,
                borderBottom: location.pathname === item.path ? '2px solid white' : 'none',
              }}
            >
              {item.label}
            </Button>
          ))}
        </Box>
      </Toolbar>
    </AppBar>
  );
}
```

**Step 2: Create api/scans.ts**

```typescript
import apiClient from './client';

export interface Scan {
  id: number;
  input_dir: string;
  output_dir: string;
  reject_dir: string;
  started_at: string;
  completed_at: string | null;
  total_images: number;
  passed_count: number;
  failed_count: number;
  status: string;
}

export async function startScan(dirs?: { input_dir?: string; output_dir?: string; reject_dir?: string }): Promise<Scan> {
  const { data } = await apiClient.post('/scans/', dirs || {});
  return data;
}

export async function getScans(limit = 20): Promise<Scan[]> {
  const { data } = await apiClient.get('/scans/', { params: { limit } });
  return data;
}

export async function getScan(scanId: number): Promise<Scan> {
  const { data } = await apiClient.get(`/scans/${scanId}`);
  return data;
}

export async function cancelScan(scanId: number): Promise<void> {
  await apiClient.post(`/scans/${scanId}/cancel`);
}
```

**Step 3: Create api/assessments.ts**

```typescript
import apiClient from './client';

export interface CategoryScore {
  category: string;
  score: number;
  reasoning: string | null;
  was_deep_dive: boolean;
}

export interface Assessment {
  id: number;
  scan_id: number;
  filename: string;
  file_path: string;
  destination_path: string | null;
  passed: boolean | null;
  triage_score: number | null;
  created_at: string;
  category_scores: CategoryScore[];
}

export interface Stats {
  total_assessed: number;
  passed: number;
  failed: number;
  pass_rate: number;
}

export async function getAssessmentsByScan(scanId: number, passed?: boolean): Promise<Assessment[]> {
  const params: Record<string, any> = {};
  if (passed !== undefined) params.passed = passed;
  const { data } = await apiClient.get(`/assessments/by-scan/${scanId}`, { params });
  return data;
}

export async function getAssessment(id: number): Promise<Assessment> {
  const { data } = await apiClient.get(`/assessments/${id}`);
  return data;
}

export async function getStats(): Promise<Stats> {
  const { data } = await apiClient.get('/assessments/stats/summary');
  return data;
}
```

**Step 4: Create api/settings.ts**

```typescript
import apiClient from './client';

export async function getAllSettings(): Promise<Record<string, string>> {
  const { data } = await apiClient.get('/settings/');
  return data;
}

export async function getSetting(key: string): Promise<string | null> {
  const { data } = await apiClient.get(`/settings/${key}`);
  return data.value;
}

export async function updateSetting(key: string, value: string): Promise<void> {
  await apiClient.put(`/settings/${key}`, { value });
}

export interface LMStudioStatus {
  connected: boolean;
  url: string;
}

export interface LMStudioModel {
  id: string;
  object: string;
}

export async function getLMStudioStatus(): Promise<LMStudioStatus> {
  const { data } = await apiClient.get('/lm-studio/status');
  return data;
}

export async function getLMStudioModels(): Promise<LMStudioModel[]> {
  const { data } = await apiClient.get('/lm-studio/models');
  return data.models || [];
}
```

**Step 5: Commit**

```bash
git add frontend/src/components/NavBar.tsx frontend/src/api/
git commit -m "feat: add NavBar component and API client functions"
```

---

## Task 8: Frontend — Dashboard Page

**Files:**
- Create: `frontend/src/pages/Dashboard.tsx`

**Step 1: Create Dashboard.tsx**

Summary stats cards + recent scans table. Follow HomeHub's responsive grid pattern (`xs={12} sm={6} md={3}` for stat cards).

Shows:
- Total images processed (card)
- Pass rate % (card)
- Passed count (card)
- Failed count (card)
- Recent scans table with: date, status, total/pass/fail counts, link to scan detail
- Quick action buttons: "New Scan" and "Settings"

Use MUI `Card`, `Typography`, `Table`, `TableHead`, `TableBody`, `TableRow`, `TableCell`, `Button`, `CircularProgress`, `Alert`, `Container`, `Grid`.

Fetch data from `getStats()` and `getScans(10)` on mount.

**Step 2: Commit**

```bash
git add frontend/src/pages/Dashboard.tsx
git commit -m "feat: add Dashboard page with stats cards and recent scans table"
```

---

## Task 9: Frontend — Settings Page

**Files:**
- Create: `frontend/src/pages/Settings.tsx`

**Step 1: Create Settings.tsx**

Settings form with:
- **LM Studio section:** URL text field, model dropdown (fetched from `/lm-studio/models`), connection status indicator
- **Directories section:** Input dir, output dir, reject dir text fields
- **Thresholds section:** 6 sliders (one per category) with numeric display, range 1-10
- **Triage section:** Borderline low/high sliders

Use MUI `TextField`, `Select`, `MenuItem`, `Slider`, `Card`, `CardContent`, `Typography`, `Button`, `Chip` (for connection status), `Divider`.

Load all settings on mount via `getAllSettings()`. Save changes via `updateSetting()` on a "Save" button click. Show success/error `Snackbar`.

**Step 2: Commit**

```bash
git add frontend/src/pages/Settings.tsx
git commit -m "feat: add Settings page with LM Studio config, directories, and threshold sliders"
```

---

## Task 10: Frontend — Scan View Page

**Files:**
- Create: `frontend/src/pages/ScanView.tsx`
- Create: `frontend/src/components/ScoreChip.tsx`

**Step 1: Create ScoreChip.tsx**

Small reusable component that shows a category score as a colored chip:
- Green (7-10): good
- Yellow/Orange (4-6): borderline
- Red (1-3): bad

```typescript
import { Chip } from '@mui/material';

interface ScoreChipProps {
  category: string;
  score: number;
}

export default function ScoreChip({ category, score }: ScoreChipProps) {
  const color = score >= 7 ? 'success' : score >= 4 ? 'warning' : 'error';
  const label = `${category.charAt(0).toUpperCase() + category.slice(1, 4)}: ${score}`;
  return <Chip label={label} color={color} size="small" sx={{ mr: 0.5 }} />;
}
```

**Step 2: Create ScanView.tsx**

Two modes:
1. **New scan mode** (no scanId param): Shows dir config fields (pre-filled from settings) + "Start Scan" button
2. **Viewing scan** (scanId param or after starting): Shows progress bar + results streaming in

Results display: table with columns:
- Thumbnail (small, from `/images/` or `/rejects/` endpoint)
- Filename
- 6 score chips (using ScoreChip component)
- Pass/Fail badge
- Deep dive indicator (icon if any category was deep-dived)
- Click row → navigate to `/assessment/:id`

Poll `getScan(scanId)` every 3 seconds while status is "running" to update progress. Poll `getAssessmentsByScan(scanId)` to stream results in.

**Step 3: Commit**

```bash
git add frontend/src/pages/ScanView.tsx frontend/src/components/ScoreChip.tsx
git commit -m "feat: add ScanView page with scan launch, progress tracking, and results table"
```

---

## Task 11: Frontend — Image Detail & History Pages

**Files:**
- Create: `frontend/src/pages/ImageDetail.tsx`
- Create: `frontend/src/pages/History.tsx`

**Step 1: Create ImageDetail.tsx**

Full-page view of a single assessment:
- Left side: full-size image (loaded from `/images/` or `/rejects/` based on pass/fail)
- Right side: card per category showing score (large), deep-dive badge, reasoning text
- Top: filename, pass/fail banner, destination path

Fetch via `getAssessment(id)` from URL param.

Use MUI `Grid` (xs={12} md={6} for image/details split), `Card`, `CardContent`, `Typography`, `Chip`, `Alert`.

**Step 2: Create History.tsx**

Browse all past scans:
- Table of scans (date, status, image counts, pass rate)
- Click a scan row → navigate to `/scan/:scanId` to see its assessments
- Filter by status dropdown (all, completed, failed, cancelled)

Fetch via `getScans(50)`.

**Step 3: Commit**

```bash
git add frontend/src/pages/ImageDetail.tsx frontend/src/pages/History.tsx
git commit -m "feat: add ImageDetail page and History page"
```

---

## Task 12: Docker Compose & Environment Config

**Files:**
- Create: `docker-compose.yml` (project root)
- Create: `.env.example` (project root)
- Create: `.gitignore` (project root)

**Step 1: Create docker-compose.yml**

```yaml
services:
  iqa-backend:
    build: ./backend
    container_name: iqa-backend
    ports:
      - "${BACKEND_PORT:-8100}:8100"
    environment:
      - DATABASE_URL=postgresql://portal_user:${POSTGRES_PASSWORD}@portal-postgres:5432/portal_db
      - LM_STUDIO_URL=${LM_STUDIO_URL:-http://host.docker.internal:1234/v1}
      - HOMEHUB_API_URL=${HOMEHUB_API_URL:-http://portal-backend:8000/api/v1}
      - IMAGE_INPUT_DIR=/app/images/input
      - IMAGE_OUTPUT_DIR=/app/images/output
      - IMAGE_REJECT_DIR=/app/images/reject
    networks:
      - portal-network
    volumes:
      - ${IMAGE_INPUT_DIR:-./.data/input}:/app/images/input:ro
      - ${IMAGE_OUTPUT_DIR:-./.data/output}:/app/images/output:rw
      - ${IMAGE_REJECT_DIR:-./.data/reject}:/app/images/reject:rw
    restart: unless-stopped

  iqa-frontend:
    build: ./frontend
    container_name: iqa-frontend
    ports:
      - "${FRONTEND_PORT:-5174}:80"
    networks:
      - portal-network
    depends_on:
      - iqa-backend
    restart: unless-stopped

networks:
  portal-network:
    external: true
    name: portal-infra_portal-network
```

**Step 2: Create .env.example**

```bash
# PostgreSQL (must match HomeHub's portal-infra/.env)
POSTGRES_PASSWORD=your_postgres_password_here

# LM Studio
LM_STUDIO_URL=http://host.docker.internal:1234/v1

# HomeHub API (for self-registration)
HOMEHUB_API_URL=http://portal-backend:8000/api/v1

# Image directories (host paths)
IMAGE_INPUT_DIR=./data/input
IMAGE_OUTPUT_DIR=./data/output
IMAGE_REJECT_DIR=./data/reject

# Ports (optional, defaults shown)
BACKEND_PORT=8100
FRONTEND_PORT=5174
```

**Step 3: Create .gitignore**

```
# Python
__pycache__/
*.pyc
.venv/
*.egg-info/

# Node
node_modules/
dist/

# Environment
.env

# Data
.data/
data/

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db
```

**Step 4: Commit**

```bash
git add docker-compose.yml .env.example .gitignore
git commit -m "feat: add Docker Compose config, env template, and gitignore"
```

---

## Task 13: Image Serving for Thumbnails

**Files:**
- Modify: `backend/app/main.py` — update static file mounts to serve from both output and reject dirs
- Create: `backend/app/api/images.py` — endpoint to serve images by assessment ID

**Step 1: Create images.py**

Serve image files by assessment ID. Determines file location from the assessment's `destination_path`.

```python
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
```

**Step 2: Add router to main.py**

Add `from app.api import images` and `app.include_router(images.router, prefix="/api/v1/images", tags=["images"])`.

**Step 3: Commit**

```bash
git add backend/app/api/images.py backend/app/main.py
git commit -m "feat: add image serving endpoint for thumbnails and full images"
```

---

## Task 14: End-to-End Testing — Manual Verification

**Step 1: Start backend locally for smoke test**

```bash
cd backend
pip install -r requirements.txt
# Ensure PostgreSQL is running (via HomeHub's Docker)
# Set DATABASE_URL, LM_STUDIO_URL env vars
uvicorn app.main:app --host 0.0.0.0 --port 8100 --reload
```

**Step 2: Verify endpoints**

```bash
# Health check
curl http://localhost:8100/health

# LM Studio status
curl http://localhost:8100/lm-studio/status

# Get settings
curl http://localhost:8100/api/v1/settings/

# List scans (empty)
curl http://localhost:8100/api/v1/scans/

# Get stats
curl http://localhost:8100/api/v1/assessments/stats/summary
```

**Step 3: Start frontend and verify UI**

```bash
cd frontend
npm install
npm run dev
# Visit http://localhost:5174
```

Verify: Dashboard loads, Settings page shows all controls, NavBar works.

**Step 4: Run a scan with test images**

Place 2-3 test images in the input directory. Start a scan via the UI or API:

```bash
curl -X POST http://localhost:8100/api/v1/scans/ -H "Content-Type: application/json" -d '{}'
```

Verify: images are assessed, scores stored in DB, files moved to output/reject dirs.

**Step 5: Commit any fixes discovered during testing**

---

## Task 15: Docker Build Verification

**Step 1: Build and run with Docker Compose**

```bash
# Ensure HomeHub's portal-network exists
docker network ls | grep portal-network

# Copy .env.example to .env and fill in values
cp .env.example .env
# Edit .env with real POSTGRES_PASSWORD

# Create data dirs
mkdir -p data/input data/output data/reject

# Build
docker compose build

# Run
docker compose up -d

# Check logs
docker compose logs -f iqa-backend
docker compose logs -f iqa-frontend
```

**Step 2: Verify HomeHub registration**

Check HomeHub dashboard — the "Image Quality Assessor" tile should appear with the magnifying glass icon.

**Step 3: Commit any Docker fixes**

```bash
git add -A
git commit -m "fix: Docker build and deployment adjustments"
```

---

## Task 16: Push to GitHub

**Step 1: Push all commits**

```bash
git push -u origin main
```

---

## Summary of Commits

1. `feat: scaffold backend with config, db session, and Dockerfile`
2. `feat: add SQLAlchemy models for scans, assessments, and settings`
3. `feat: add LM Studio client and expert rubric prompts for 6-category assessment`
4. `feat: add hybrid triage assessment engine and file manager`
5. `feat: add API routes for scans, assessments, settings, and HomeHub registration`
6. `feat: scaffold frontend with React, MUI, Vite, and HomeHub-matching theme`
7. `feat: add NavBar component and API client functions`
8. `feat: add Dashboard page with stats cards and recent scans table`
9. `feat: add Settings page with LM Studio config, directories, and threshold sliders`
10. `feat: add ScanView page with scan launch, progress tracking, and results table`
11. `feat: add ImageDetail page and History page`
12. `feat: add Docker Compose config, env template, and gitignore`
13. `feat: add image serving endpoint for thumbnails and full images`
14. Manual verification (fix commits as needed)
15. Docker verification (fix commits as needed)
16. Push to GitHub
