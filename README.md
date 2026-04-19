# Image Quality Assessor (IQA)

> Vision-LLM powered quality triage for AI-generated images — scores and auto-sorts text-to-image outputs against a structured rubric.

## About

IQA is a self-hosted web app that uses a vision-enabled LLM (e.g. Qwen VL via LM Studio) to grade text-to-image generations on anatomy, composition, lighting, realism, prompt adherence, and technical quality. It runs a fast triage pass over a directory of images, does a targeted deep-dive on borderline cases, and auto-sorts passes and rejects into separate folders. Designed to plug into the HomeHub portal ecosystem (shared PostgreSQL, portal network, registered app tile), but runs standalone too.

## Getting Started

### Prerequisites

- Docker and Docker Compose
- A running [LM Studio](https://lmstudio.ai/) instance serving a vision model (default: `qwen/qwen3-vl-8b`) on an OpenAI-compatible endpoint
- PostgreSQL — either the HomeHub `portal-infra` stack, or your own instance (update `DATABASE_URL` to match)
- For local dev without Docker: Python 3.11+ and Node.js 18+

### Installation

```bash
# Clone the repository
git clone https://github.com/cochbild/image-quality.git
cd image-quality

# Configure environment
cp .env.example .env
# Edit .env — set POSTGRES_PASSWORD, LM_STUDIO_URL, and image directories

# Build and run
docker compose build
docker compose up -d
```

The frontend serves on `http://localhost:5180` and the backend API on `http://localhost:8100` by default.

### Local Development

```bash
# Backend
cd backend
python -m venv .venv && source .venv/Scripts/activate  # Windows bash
pip install -r requirements.txt
uvicorn app.main:app --port 8100 --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

## Features

- **Hybrid triage** — fast overall scoring pass, with conditional deep-dive only on borderline categories
- **Six-category rubric** — anatomy, composition, lighting, realism, prompt adherence, technical quality (per-category thresholds configurable)
- **Auto-sorting** — passes, rejects, and originals routed to separate directories by outcome
- **Scan history** — browse past scans and drill into per-image category scores with model reasoning
- **LM Studio integration** — OpenAI-compatible vision endpoint; model selection filtered to VLMs only
- **HomeHub tile** — self-registers with the HomeHub portal when `HOMEHUB_API_URL` is set
- **React + MUI frontend** — dashboard, scan runner with live progress, settings, image detail view

## Tech Stack

- **Backend:** FastAPI, SQLAlchemy 2.0, Pydantic v2, httpx, Pillow
- **Frontend:** React 18, TypeScript, Vite, MUI v7, Axios
- **Database:** PostgreSQL 15 (tables prefixed `iqa_`)
- **Infra:** Docker Compose, nginx (frontend serving)

## Repository Layout

```
backend/    FastAPI app — API routes, assessment engine, LM Studio client, rubric
frontend/   React + Vite UI — dashboard, scan view, settings, history, image detail
docs/       Design notes and implementation plan
```

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](https://github.com/cochbild/.github/blob/main/CONTRIBUTING.md) for guidelines.

## Security

Please see [SECURITY.md](SECURITY.md) for the vulnerability reporting policy.

## License

MIT — see [LICENSE](LICENSE) for details.

## Contact

**Dale Cochran** — [@cochbild](https://github.com/cochbild)
