# IMPLEMENTATION_PLAN.md

Status: `IN PROGRESS` · 11 phases, mirrors the required execution sequence.

Status legend: `NOT STARTED` · `IN PROGRESS` · `BLOCKED` · `IMPLEMENTED` · `TESTED` · `VERIFIED`

---

| Phase | Name | Status |
|---|---|---|
| 1 | Requirement analysis | **IN PROGRESS** |
| 2 | Technical architecture | **IN PROGRESS** |
| 3 | Project setup | NOT STARTED |
| 4 | Database & backend | NOT STARTED |
| 5 | Frontend & UI | NOT STARTED |
| 6 | API & third-party integration | NOT STARTED |
| 7 | Feature integration | NOT STARTED |
| 8 | Testing & debugging | NOT STARTED |
| 9 | Performance optimization | NOT STARTED |
| 10 | Production deployment | NOT STARTED |
| 11 | Final verification & documentation | NOT STARTED |

---

## Phase 1 — Requirement analysis
- [x] Read TELIPORT brief + case study PDF (extracted to text)
- [x] Capture judging weights and submission rules
- [ ] Confirm Round-1 status / Round-2 eligibility with team
- [x] `PROJECT_REQUIREMENTS.md` written

## Phase 2 — Technical architecture
- [x] Layer-by-layer architecture designed
- [x] Stack selected with rationale
- [x] Data model + API surface drafted
- [x] Triage-agent rule draft written
- [ ] Get team sign-off on the two open decisions (subset, dashboard)

## Phase 3 — Project setup
- [ ] Create repo skeleton (folders above)
- [ ] Python venv + `requirements.txt` (pandas, numpy, scikit-learn, mlflow, fastapi, uvicorn, pytest)
- [ ] Download **NASA C-MAPSS** → `data/raw/` (verify license/terms)
- [ ] Frontend scaffold (Vite + React + Tailwind)
- [ ] Pre-commit basics: `.gitignore` (data, mlruns, .env), `.env.example`

## Phase 4 — Database & backend
- [ ] SQLite schema + migrations (engines, predictions, work_orders, model_runs, sensor_snapshots)
- [ ] FastAPI app with the endpoints in `TECHNICAL_ARCHITECTURE.md` §5
- [ ] Pydantic validation + basic token auth on mutations

## Phase 5 — Frontend & UI
- [ ] Design system (palette, typography, spacing, components)
- [ ] Pages: Fleet Dashboard · Engine Detail · Work Orders · Models & Monitoring · About
- [ ] Loading / empty / error / success states everywhere
- [ ] Responsive (mobile → desktop) + keyboard navigation

## Phase 6 — API & third-party integration
- [ ] Frontend ↔ FastAPI wired to real data (no fake buttons)
- [ ] MLflow tracking wired into `train.py` / `retrain.py`
- [ ] NASA dataset ingestion (real files, not hardcoded samples)

## Phase 7 — Feature integration
- [ ] End-to-end run: data → features → model → agent → work order (single command)
- [ ] Human exception queue (approve / override / dismiss) functional
- [ ] Demo retraining run wired to the dashboard button

## Phase 8 — Testing & debugging
- [ ] pytest: feature engineering correctness, RUL label logic, agent rules, API contracts
- [ ] Pipeline reproducibility test (same seed → same metrics)
- [ ] Browser journey test on the deployed URL (console clean, no dead links)

## Phase 9 — Performance optimization
- [ ] Feature pipeline runtime check; cache processed features
- [ ] Frontend bundle budget; lazy-load heavy charts
- [ ] API response times < 500 ms for dashboard calls

## Phase 10 — Production deployment
- [ ] See `DEPLOYMENT_PLAN.md`
- [ ] Deploy backend → Render; frontend → Vercel
- [ ] Verify live URL end-to-end (never claim deployed without checking)

## Phase 11 — Final verification & documentation
- [ ] `README.md`, `TEST_REPORT.md`, `DEPLOYMENT_STATUS.md`
- [ ] Round-2 deck (10 slides) + demo walkthrough script
- [ ] Final submission checklist (naming convention, <5 MB, leader-only upload)

---

## Timeline (working backwards from the Round-2 deadline)

| Date | Milestone |
|---|---|
| **Now → 13 Nov** | Phases 1–4: docs, repo, data, working pipeline + model |
| **14 Nov 10:00** | Round 2 window opens — submission-ready PoC target |
| 14 → 30 Nov | Phases 5–8: dashboard, integration, testing |
| 1 → 8 Dec | Phase 9–10: polish, deploy, record demo |
| 9 → 12 Dec | Phase 11: deck, dry-run, upload **before** 13 Dec 23:59 |

## Open questions (need team input)
1. **Round-1 status** — was the design deck submitted before 2 Nov 08:00? Are we shortlisted for Round 2?
2. **Dataset subset** — FD001 only (default) vs all four (raises "Dataset coverage" 10%)
3. **Dashboard tech** — React+FastAPI (default, recommended) vs Streamlit (faster, case-study suggestion)
4. Team name / institute name / leader name (needed for the submission file naming)
