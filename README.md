# Self-Healing Machines

**Predictive maintenance for a connected fleet — from sensor history to an automatic work order, with no manual steps in between.**

A round-2 prototype for the TELIPORT Case Study 1, built on the NASA C-MAPSS turbofan benchmark.

```
sensor stream → clean + rolling features → RUL prediction + anomaly score
             → rule-based triage agent → automatic work order
             → human only sees the exceptions
```

No LLM is used anywhere in the runtime path: every decision is a documented threshold.

---

## What is in the box

| Layer | Implementation |
|---|---|
| Data engineering | Validated C-MAPSS ingestion, per-engine cleaning, rolling mean/std/trend, RUL labels, parquet exports with sha256 manifests |
| ML | Ridge baseline vs HistGradientBoosting RUL regressor + IsolationForest anomaly detector, engine-level split (no leakage) |
| MLOps | MLflow tracking, versioned production pointer, retraining job, metrics mirrored into SQLite |
| Triage agent | Deterministic rules on RUL + anomaly + RUL slope → CRITICAL / HIGH / MEDIUM / LOW |
| API | FastAPI, typed schemas, CORS, optional write token, background retrain job |
| Dashboard | React + Vite + Tailwind + Recharts: fleet, engine detail, work orders, models, about |

### Recorded results (FD001, verified 2026-11-05)

| Metric | Ridge baseline | Gradient boosting |
|---|---|---|
| Validation RMSE | 21.02 cycles | **17.59 cycles** |
| Validation MAE | 17.34 | **13.16** |
| Critical recall (validation) | 0.528 | **0.825** |

Official test split (100 engines, scored at each engine's last cycle):
**RMSE 18.73 · MAE 13.64 · PHM 1087 · critical recall 0.90**.

These numbers are produced by `pipeline/train.py` and stored in `models/production.json`
and `data/shm.db` — they are not hand-written.

---

## Screens

1. **Fleet overview** — KPI cards, severity distribution, 100 machines ranked by urgency.
2. **Engine detail** — predicted RUL over time, anomaly percentile, agent audit trail.
3. **Work orders** — auto-created queue + human exception queue, resolve/dismiss.
4. **Models & monitoring** — baseline vs candidate, run history, RUL distribution, **Retrain** button.
5. **About** — architecture, dataset provenance, known limitations.

The demo moment: press **Retrain & re-score fleet** → a new model version is fitted,
promoted, the whole fleet is re-scored and the work-order queue is rebuilt. The API
returns real validation and test metrics for the new run.

---

## Repository layout

```
pipeline/          ingest → features → train → predict → triage → store
backend/app/       FastAPI: config, schemas, main (routes + retrain worker)
frontend/          React dashboard (Vite, TypeScript, Tailwind, Recharts)
scripts/           dataset inspection report
tests/             63 tests: pipeline, store, API, dataset determinism
data/              raw NASA files (FD001 committed for retraining), seeded shm.db
models/            fitted joblib models + production.json
render.yaml        Render blueprint for the API
frontend/vercel.json  SPA rewrites for Vercel
```

---

## Run locally

Prerequisites: Python 3.12+, Node 20+.

```powershell
# 1. Python environment
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt

# 2. Build the processed dataset (optional, proves the data layer)
.venv\Scripts\python.exe -m pipeline.dataset --subsets all

# 3. Train + score + persist the fleet (creates data/shm.db)
.venv\Scripts\python.exe -m pipeline.store

# 4. API  → http://localhost:8000/docs
.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload

# 5. Dashboard → http://localhost:5173  (in a second terminal)
cd frontend
npm install
npm run dev
```

The frontend defaults to `http://localhost:8000`; override with `frontend/.env.local`:

```
VITE_API_URL=http://localhost:8000
```

### Tests

```powershell
.venv\Scripts\python.exe -m pytest          # 63 passed, 9 skipped
cd frontend; npm run build                  # type-check + production build
```

---

## Deployment

Frontend on **Vercel**, API on **Render** (free tier). Full click-by-click steps:
[`DEPLOY.md`](DEPLOY.md).

- Vercel project root directory: `frontend`
- Vercel env: `VITE_API_URL=https://<your-service>.onrender.com`
- Render: import the repo and apply `render.yaml`

Free-tier caveats (documented, not hidden): the API sleeps after ~15 minutes and
its disk is ephemeral, so work-order resolutions reset on redeploy. Retraining
works because the FD001 raw files and fitted models are committed.

---

## Dataset & licence

NASA C-MAPSS Turbofan Engine Degradation Simulation Data Set, NASA Prognostics
Center of Excellence — a U.S. Government work in the public domain.
Download instructions: [`data/README.md`](data/README.md).

Predictions are benchmark results on simulated engines, not operational advice
for real assets.
