# Image Quality Assessor (IQA) - Design Document

**Date:** 2026-02-28
**Status:** Approved
**Repository:** https://github.com/cochbild/image-quality

## Purpose

A web application that uses vision-enabled LLMs (Qwen VL via LM Studio) to automatically assess the quality of text-to-image (t2i) generated images. It detects common t2i defects (deformed hands, bad faces, merged bodies, physics violations, etc.) using a structured rubric, scores each image, and auto-sorts passing/failing images into separate directories.

Integrates with the HomeHub portal ecosystem, sharing its PostgreSQL database and registering as a visible app tile.

## Tech Stack

Matches HomeHub conventions:

- **Frontend:** React 18 + TypeScript + Vite + MUI v7 + Emotion + Axios
- **Backend:** FastAPI + Python 3.11 + SQLAlchemy 2.0 + Pydantic v2
- **Database:** Shared PostgreSQL 15 (portal_db), tables prefixed `iqa_`
- **Infrastructure:** Docker Compose, connects to HomeHub's portal-network
- **Vision API:** LM Studio OpenAI-compatible endpoint (configurable, default `http://localhost:1234/v1`)

## Assessment Approach: Hybrid Triage

### Phase 1 - Triage Pass
Send each image to the vision model with a quick overall assessment prompt. The model returns a confidence estimate per rubric category (1-10).

### Phase 2 - Deep Dive (Conditional)
Categories scoring in the borderline zone (4-8) trigger a focused deep-dive prompt for that specific category only. Clear passes (9-10) and clear fails (1-3) skip the deep dive.

### Rationale
- Fast for obvious passes/fails (majority of images)
- Deep analysis only where it matters (borderline cases)
- Balances speed with accuracy

## Quality Assessment Rubric

Six categories, each scored 1-10. An image must meet the minimum score in ALL categories to pass. Failing any single category = reject.

### Category 1: Anatomical Integrity (default min: 7)

Detects human body defects - the #1 failure mode in t2i images.

**Evaluates:**
- **Hands:** Finger count (exactly 5 per hand), finger proportions, joint articulation, nail placement, thumb position
- **Face:** Eye symmetry and count, pupil shape, mouth/teeth integrity, ear placement, nose structure, natural skin texture
- **Body:** Correct limb count, no merged bodies, anatomically possible joint angles, proportional limbs/torso/neck
- **Feet:** Correct toe count, no fused feet, proper orientation

**Scoring guide:**
- 10: Flawless human anatomy
- 7-9: Minor imperfections (slightly off proportions, minor asymmetry)
- 4-6: Noticeable issues (extra/missing finger, mild face distortion)
- 1-3: Severe deformations (merged bodies, extra limbs, melted faces)

### Category 2: Compositional Coherence (default min: 6)

Evaluates scene structure and spatial relationships.

**Evaluates:**
- Object scale consistency (no cups larger than people)
- Perspective/vanishing point consistency
- Foreground-background relationship integrity
- No floating or gravity-defying objects (without justification)
- No object merging/fusion artifacts

### Category 3: Physics & Lighting (default min: 6)

Checks physical plausibility of the scene.

**Evaluates:**
- Shadow direction consistency (single light source or justified multi-source)
- Shadow presence for all grounded objects
- Reflection accuracy in mirrors/water/glass
- Consistent depth-of-field behavior
- Gravity and structural support logic

### Category 4: Texture & Surface Quality (default min: 5)

Assesses material rendering quality.

**Evaluates:**
- Skin texture realism (no waxy/plastic appearance, has pores and micro-details)
- Hair rendering quality (natural variation, proper physics)
- Fabric/clothing integrity (correct folds, no pattern warping, functional design)
- Material property consistency (metal looks metallic, glass is translucent)
- No edge bleeding or texture leaking between objects

### Category 5: Technical Quality (default min: 5)

Catches rendering artifacts.

**Evaluates:**
- No visible noise patches or denoising artifacts
- No color banding in gradients
- Consistent resolution across the image
- No tiling or repeating pattern artifacts
- No watermark-like ghost patterns
- Clean edges without halos or aliasing

### Category 6: Semantic Integrity (default min: 6)

Checks logical consistency.

**Evaluates:**
- Text rendering quality (if text present - readable, correct spelling)
- Correct object counts matching scene expectations
- Contextually appropriate combinations (no bathing suits at funerals)
- No hybrid/contradictory object states
- Logical spatial relationships between objects

## Triage Logic

The initial quick pass produces a confidence estimate per category:
- **Clear pass (9-10):** Skip deep dive for this category
- **Borderline (4-8):** Trigger focused deep-dive prompt for this category
- **Clear fail (1-3):** Skip deep dive, mark as failed immediately

The borderline zone range (default 4-8) is configurable in settings.

## Web UI

### Pages

**1. Dashboard**
- Summary stats: total images processed, pass rate, average scores per category
- Recent assessment results in a sortable table
- Quick actions: start new scan, view settings

**2. Scan View**
- Configure: select input directory, output/reject directories
- Start scan button with progress indicator showing current image
- Results stream in as each image completes
- Each result row: thumbnail, category scores (color-coded green/yellow/red), pass/fail badge, triage/deep-dive indicator

**3. Image Detail**
- Full-size image display
- Category-by-category scores with the model's reasoning text
- Which categories triggered deep-dive (if any)
- Pass/fail status, file destination path

**4. History**
- Browse past scan results
- Filterable by date, pass/fail status, score ranges
- Sortable by any category score

**5. Settings**
- LM Studio endpoint URL (default: `http://localhost:1234/v1`) + model selection dropdown (fetched from /models)
- Input/output/reject directory paths
- Category minimum thresholds (6 sliders with numeric display)
- Borderline zone range for triage (default 4-8)

### UI Style
- Matches HomeHub: MUI v7, Roboto font, primary #1976d2, 12px card border radius
- All styling via MUI `sx` prop
- Responsive grid layout following HomeHub patterns

## Database Schema

All tables in shared `portal_db`, prefixed with `iqa_`.

```sql
-- Scan session tracking
CREATE TABLE iqa_scans (
    id SERIAL PRIMARY KEY,
    input_dir VARCHAR NOT NULL,
    output_dir VARCHAR NOT NULL,
    reject_dir VARCHAR NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    total_images INTEGER NOT NULL DEFAULT 0,
    passed_count INTEGER NOT NULL DEFAULT 0,
    failed_count INTEGER NOT NULL DEFAULT 0,
    status VARCHAR NOT NULL DEFAULT 'running'  -- running, completed, failed, cancelled
);

-- Individual image assessment
CREATE TABLE iqa_assessments (
    id SERIAL PRIMARY KEY,
    scan_id INTEGER NOT NULL REFERENCES iqa_scans(id) ON DELETE CASCADE,
    filename VARCHAR NOT NULL,
    file_path VARCHAR NOT NULL,
    destination_path VARCHAR,
    passed BOOLEAN,
    triage_score FLOAT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Per-category scores
CREATE TABLE iqa_category_scores (
    id SERIAL PRIMARY KEY,
    assessment_id INTEGER NOT NULL REFERENCES iqa_assessments(id) ON DELETE CASCADE,
    category VARCHAR NOT NULL,  -- anatomical, compositional, physics, texture, technical, semantic
    score INTEGER NOT NULL CHECK (score >= 1 AND score <= 10),
    reasoning TEXT,
    was_deep_dive BOOLEAN NOT NULL DEFAULT FALSE
);

-- App settings (key-value)
CREATE TABLE iqa_settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR NOT NULL UNIQUE,
    value TEXT NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

## Auto-Sort Behavior

After assessment completes for an image:
- **Pass (all categories meet minimums):** Move file from input_dir to output_dir
- **Fail (any category below minimum):** Move file from input_dir to reject_dir
- Filenames are preserved. Collisions are handled by appending a numeric suffix.

## HomeHub Integration

### Self-Registration

On backend startup, registers with HomeHub:
```
POST http://portal-backend:8000/api/v1/apps/register
{
    "name": "Image Quality Assessor",
    "slug": "image-quality",
    "description": "AI-powered quality assessment for t2i generated images",
    "icon": "🔍",
    "external_url": "http://localhost:5174",
    "dev_url": "http://localhost:5174",
    "category": "tools",
    "ports": [
        {"port": 8100, "protocol": "HTTP", "purpose": "IQA Backend API", "mode": "both"},
        {"port": 5174, "protocol": "HTTP", "purpose": "IQA Frontend (dev)", "mode": "development"}
    ]
}
```

The returned API key is stored for future updates.

### Docker Compose

```yaml
services:
  iqa-backend:
    build: ./backend
    container_name: iqa-backend
    ports: ["8100:8100"]
    environment:
      - DATABASE_URL=postgresql://portal_user:${POSTGRES_PASSWORD}@portal-postgres:5432/portal_db
      - LM_STUDIO_URL=${LM_STUDIO_URL:-http://host.docker.internal:1234/v1}
      - HOMEHUB_API_URL=http://portal-backend:8000/api/v1
    networks:
      - portal-network
    volumes:
      - ${IMAGE_INPUT_DIR}:/app/images/input:ro
      - ${IMAGE_OUTPUT_DIR}:/app/images/output:rw
      - ${IMAGE_REJECT_DIR}:/app/images/reject:rw
    restart: unless-stopped

  iqa-frontend:
    build: ./frontend
    container_name: iqa-frontend
    ports: ["5174:80"]
    networks:
      - portal-network
    restart: unless-stopped

networks:
  portal-network:
    external: true
    name: portal-infra_portal-network
```

### Directory Mounting
- Input directory: read-only mount (source images are not modified in-place)
- Output/reject directories: read-write mount (files moved here after assessment)
- Paths configurable via `.env` and overridable in Settings UI

### LM Studio Connection
- Default: `http://host.docker.internal:1234/v1` (reaches host machine from Docker)
- Fully configurable via Settings UI and `LM_STUDIO_URL` env var
- Model selection dropdown populated from LM Studio's `GET /models` endpoint

## Project Structure

```
image-quality/
├── frontend/                    # React + TypeScript + Vite
│   ├── src/
│   │   ├── api/                 # Axios client, API call functions
│   │   ├── components/          # Reusable MUI components
│   │   ├── pages/               # Dashboard, ScanView, ImageDetail, History, Settings
│   │   ├── theme.ts             # MUI theme (matching HomeHub)
│   │   ├── App.tsx              # Router setup
│   │   └── main.tsx             # Entry point
│   ├── Dockerfile               # Multi-stage Node + Nginx
│   ├── nginx.conf
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── backend/                     # FastAPI + Python
│   ├── app/
│   │   ├── api/                 # Route handlers (scans, assessments, settings)
│   │   ├── core/                # Config, LM Studio client
│   │   ├── db/                  # SQLAlchemy models, session
│   │   ├── services/            # Assessment engine, file manager, rubric prompts
│   │   └── main.py              # FastAPI app, startup registration
│   ├── Dockerfile
│   └── requirements.txt
├── docker-compose.yml
├── .env.example
├── docs/plans/
│   └── 2026-02-28-image-quality-assessor-design.md
└── README.md
```

## Research References

Key defect categories derived from:
- CHI 2025 artifact taxonomy (5 dimensions, 749K+ observations)
- HADM (Human Artifact Detection Model) - 12-class human artifact taxonomy
- AnomReason benchmark - 21,539 images, 127K+ verified anomalies
- ImageDoctor (2025) - plausibility/alignment/aesthetics scoring
- RichHF-18K (CVPR 2024 Best Paper) - rich feedback annotation framework
