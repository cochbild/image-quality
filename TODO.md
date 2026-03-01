# Image Quality Assessor - TODO

## Completed
- [x] Backend scaffolding (config, db session, Dockerfile)
- [x] Database models (Scan, Assessment, CategoryScore, Setting)
- [x] LM Studio client & rubric prompts (6-category triage + deep-dive)
- [x] Assessment engine (hybrid triage) & file manager (auto-sort)
- [x] Backend API routes (scans, assessments, settings, health, HomeHub registration)
- [x] Frontend scaffolding (React, Vite, MUI v7, theme, API client)
- [x] NavBar component & API client functions
- [x] Dashboard page (stats cards, recent scans table)
- [x] Settings page (LM Studio config, directories, threshold sliders, triage settings)
- [x] ScanView page (scan launch, progress tracking, results table, ScoreChip)
- [x] ImageDetail page (full image + per-category score cards with reasoning)
- [x] History page (past scans browser with status filter)
- [x] Docker Compose & environment config (.env.example, .gitignore)
- [x] Image serving endpoint (serve images by assessment ID)

## Remaining
- [ ] Run `npm install` in `frontend/` directory
- [ ] Run `pip install -r requirements.txt` in `backend/` directory
- [ ] Verify frontend builds: `cd frontend && npm run build`
- [ ] Verify backend starts: `cd backend && uvicorn app.main:app --port 8100`
- [ ] Test with Docker Compose: `docker compose build && docker compose up`
- [ ] Verify HomeHub registration (check portal dashboard for IQA tile)
- [ ] End-to-end test: place test images in input dir, run a scan, verify sorting
- [ ] Add README.md with setup instructions
