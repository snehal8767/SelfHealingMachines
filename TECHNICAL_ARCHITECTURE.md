# TECHNICAL_ARCHITECTURE.md

Status: `IN PROGRESS` — Phase 2

---

## 1. Architecture overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│  NASA C-MAPSS (FD001…FD004)  —  train_FD001.txt / test_FD001.txt / RUL │
└───────────────────────────────┬─────────────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 1 · DATA ENGINEERING                                               │
│  ingest → validate schema → handle missing/noise → normalize per-engine  │
│  → rolling-window features (mean, std, slope over W cycles) → RUL label  │
└───────────────────────────────┬─────────────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 2 · MACHINE LEARNING                                               │
│  • RUL regression: Gradient Boosting (primary) vs Linear/Ridge (baseline)│
│  • Anomaly detection: IsolationForest on healthy-regime features         │
│  • Evaluation: RMSE, MAE, NASA PHM scoring function, failure recall      │
└───────────────────────────────┬─────────────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 3 · MLOPS                                                          │
│  MLflow tracking (params, metrics, artifacts) → model registry/version  │
│  retrain pipeline (triggered by "new data" file drop) → monitoring view  │
└───────────────────────────────┬─────────────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 4 · TRIAGE AGENT (rules only — NO LLM)                             │
│  input: RUL prediction + anomaly score + trend                           │
│  → severity = f(RUL band, anomaly, degradation slope)                    │
│  → CRITICAL/HIGH → auto work order · MEDIUM → queue for human · LOW → log│
└───────────────────────────────┬─────────────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  WORK ORDER STORE (SQLite)  →  FastAPI  →  React dashboard               │
│   • human exception queue (approve / override / dismiss)                 │
│   • model monitoring page · RUL countdown per engine                     │
└─────────────────────────────────────────────────────────────────────────┘
```

**Closed loop:** new sensor file arrives → retrain pipeline → new model version in MLflow
→ agent starts using it → work orders reflect the new model → dashboard shows both.

## 2. Technology choices and why

| Concern | Choice | Why |
|---|---|---|
| Language | Python 3.12 | Case-study suggestion; ML ecosystem |
| Data | **pandas + numpy** | Explicitly suggested; enough for FD001–FD004 |
| ML | **scikit-learn** (GradientBoosting / RandomForest / Ridge / IsolationForest) | Suggested, lightweight, no GPU needed, easy to explain in review |
| Experiment tracking | **MLflow** (local file store by default) | Explicitly suggested; gives model versions + retraining story |
| Backend API | **FastAPI + SQLite** | Proven in CitrusGuardAI; serves the dashboard and agent actions |
| Frontend | **React + Vite + Tailwind** | Premium UI is a judging factor; team already has a working Vercel pipeline |
| Deployment | **Vercel** (frontend) + **Render** (API) | Already-proven pipeline from CitrusGuardAI |
| Agent | Plain Python rule engine | G3 forbids LLM/agent frameworks |

**Considered and rejected for v1:** Streamlit/Dash (suggested but optional) — a custom React
dashboard scores better on "Demo & explanation" (20%) and reuses the team's proven deploy path.
PySpark — unnecessary at this dataset size. TensorFlow/PyTorch — not needed to beat the baseline.

## 3. Repository structure

```
SelfHealingMachines/
├── PROJECT_REQUIREMENTS.md      ← this phase
├── TECHNICAL_ARCHITECTURE.md
├── IMPLEMENTATION_PLAN.md
├── FEATURE_CHECKLIST.md
├── DEPLOYMENT_PLAN.md
├── data/
│   ├── raw/                     ← NASA files (not committed if license-sensitive)
│   └── processed/               ← engineered features (regenerable)
├── pipeline/
│   ├── ingest.py                ← load + validate
│   ├── features.py              ← cleaning + rolling windows + RUL labels
│   ├── train.py                 ← trains baseline + candidate, logs to MLflow
│   ├── predict.py               ← batch inference → predictions table
│   ├── retrain.py               ← "new data arrived" entry point
│   └── triage.py                ← rule-based agent → work orders
├── mlruns/                      ← MLflow local tracking (git-ignored)
├── backend/
│   └── app/                     ← FastAPI: predictions, work orders, metrics, retrain trigger
├── frontend/                    ← React dashboard (Vercel)
└── tests/                       ← pytest for pipeline + API
```

## 4. Data model (SQLite)

| Table | Purpose | Key columns |
|---|---|---|
| `engines` | fleet master | `engine_id, subset, total_cycles` |
| `predictions` | one row per engine per run | `engine_id, run_id, predicted_rul, anomaly_score, severity, created_at` |
| `work_orders` | agent output | `id, engine_id, severity, reason, status(open/human_review/closed), created_at` |
| `model_runs` | MLOps audit | `run_id, mlflow_run_id, rmse, mae, phm_score, trained_at, is_production` |
| `sensor_snapshots` | latest raw reading per engine | `engine_id, cycle, sensor_1…21, setting_1…3` |

## 5. API surface (FastAPI)

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | liveness |
| GET | `/fleet` | engines + latest RUL + severity |
| GET | `/engines/{id}` | sensor history, feature trends, RUL countdown |
| GET | `/predictions?run_id=` | batch results |
| GET | `/work-orders` | list + filters |
| POST | `/work-orders/{id}/resolve` | **human** exception handling |
| GET | `/models` | MLflow runs, metrics, production version |
| POST | `/retrain` | triggers demo retraining run |
| GET | `/monitoring` | metric/drift summary for the dashboard |

## 6. Triage Agent rules (no LLM)

```
severity = CRITICAL  if predicted_RUL ≤ 15  OR anomaly ≥ 0.999
severity = HIGH      if predicted_RUL ≤ 30  OR (anomaly ≥ 0.997 AND rul_slope < -1.5)
severity = MEDIUM    if predicted_RUL ≤ 60  OR anomaly ≥ 0.95
severity = LOW       otherwise

rul_slope = per-cycle change of *predicted* RUL over the last 5 cycles
            (≈ -1 for a machine ageing normally, much worse when life burns fast)

action:
  CRITICAL, HIGH → create work order automatically (status = OPEN)
  MEDIUM         → create work order (status = HUMAN_REVIEW)  ← human steps in
  LOW            → log only, no work order
```

**How the bands were set** — leak-free calibration on *validation* engines only
(the test split is never used for operational decisions). Sampling each engine
at known life points gave these anomaly percentiles:

| true RUL left | predicted RUL (median) | anomaly (median) |
|---|---|---|
| 100 | 103.2 | 0.52 |
| 50 | 58.9 | 0.97 |
| 30 | 33.7 | 0.997 |
| 15 | 15.7 | 1.000 |
| 10 | 10.2 | 1.000 |

With bands 0.95 / 0.997 / 0.999 the resulting decision quality was:
**0%** severe at 100 cycles left, **22%** at 50, **60%** at 30, **98–100%** at
≤15 — calm machines stay off the queue, dying ones cannot. `CRITICAL_RUL` in the
rules is *derived from* the model's critical-recall threshold, so agent and
metrics can never disagree. Thresholds are logged as parameters in MLflow.

## 7. Security notes
- No secrets in the repo; `.env.example` only
- API read endpoints public (demo), **mutating** endpoints (`/resolve`, `/retrain`) require a token
- Inputs validated with Pydantic; SQL via ORM/parameterised queries
- Honest limitation: this is a hackathon demo, not a hardened multi-tenant product
