# FEATURE_CHECKLIST.md

Status legend: `NOT STARTED` · `IN PROGRESS` · `BLOCKED` · `IMPLEMENTED` · `TESTED` · `VERIFIED`

> A feature is **TESTED** when pytest proves it locally; it becomes **VERIFIED**
> only after it has been demonstrated working **on the deployed URL**.
> Code existing is not enough for either.

**Last updated: 2026-11-04** — 42 pytest green (`pytest tests`, ~25 s).

---

## Layer 1 — Data Engineering
| # | Feature | Status |
|---|---|---|
| 1.1 | Load NASA C-MAPSS files (train/test/RUL) for chosen subset(s) | **TESTED** |
| 1.2 | Schema validation + missing-value handling | **TESTED** |
| 1.3 | Basic noise handling / normalisation | **TESTED** — rolling smoothing in features; feature scaling happens in the model pipeline (Ridge) |
| 1.4 | Rolling-window features (mean, std, trend) | **TESTED** |
| 1.5 | RUL label construction (train clipped at 125, test truth unclipped) | **TESTED** |
| 1.6 | Reproducible, one-command feature build | **TESTED** |

## Layer 2 — Machine Learning
| # | Feature | Status |
|---|---|---|
| 2.1 | Baseline RUL model (StandardScaler → Ridge) | **TESTED** |
| 2.2 | Primary RUL model (HistGradientBoosting, reasoning documented) | **TESTED** — FD001 val RMSE 17.6 vs baseline 21.0 |
| 2.3 | Anomaly detection (IsolationForest on healthy regime → 0–1 percentile) | **TESTED** |
| 2.4 | Evaluation: RMSE, MAE, NASA PHM score, critical recall | **TESTED** — official test split: RMSE 18.73, MAE 13.64, PHM 1087, recall 0.90 |
| 2.5 | Handles mild class imbalance deliberately | **TESTED** — critical-recall metric + agent thresholds, documented |
| 2.6 | Inference: score fleet, current-state protocol, schema-drift guard | **TESTED** |

## Layer 3 — MLOps
| # | Feature | Status |
|---|---|---|
| 3.1 | MLflow experiment tracking (params + metrics + artifacts) | **TESTED** — SQLite backend, run `da8a51ab…` verified |
| 3.2 | Model versioning / production pointer (`models/production.json`, selection rule = lowest RMSE) | **TESTED** |
| 3.3 | Retraining flow triggered by "new data" | NOT STARTED |
| 3.4 | Monitoring view (metric trends, RUL distribution, drift signal) | NOT STARTED |

## Layer 4 — Triage Agent (no LLM)
| # | Feature | Status |
|---|---|---|
| 4.1 | Rule engine: RUL + anomaly + trend → severity | **TESTED** — bands calibrated on validation engines only |
| 4.2 | Auto-create work order for CRITICAL/HIGH | **TESTED** (logic + status mapping; not yet persisted) |
| 4.3 | Human exception queue for MEDIUM (approve/override/dismiss) | NOT STARTED — needs DB + API + UI |
| 4.4 | Full audit trail of agent decisions | NOT STARTED — needs `agent_log` table |

## Application — Backend (FastAPI)
| # | Feature | Status |
|---|---|---|
| B.1 | `/health`, `/fleet`, `/engines/{id}` | NOT STARTED |
| B.2 | `/predictions`, `/work-orders` + resolve | NOT STARTED |
| B.3 | `/models`, `/monitoring`, `/retrain` | NOT STARTED |
| B.4 | Input validation, error handling, token on mutations | NOT STARTED |

## Application — Frontend (React)
| # | Feature | Status |
|---|---|---|
| F.1 | Fleet dashboard (RUL countdown, severity chips, KPIs) | NOT STARTED |
| F.2 | Engine detail (sensor trends, feature charts, prediction) | NOT STARTED |
| F.3 | Work orders page (queue, filters, human actions) | NOT STARTED |
| F.4 | Models & monitoring page (MLflow runs, metrics, retrain button) | NOT STARTED |
| F.5 | Loading / empty / error / success states | NOT STARTED |
| F.6 | Responsive + accessible (keyboard, contrast, aria) | NOT STARTED |

## Quality
| # | Feature | Status |
|---|---|---|
| Q.1 | pytest suite green | **TESTED** — 42 passed |
| Q.2 | Production build + TypeScript checks pass | NOT STARTED (frontend not scaffolded) |
| Q.3 | No fake buttons / dead links / hardcoded demo data presented as real | NOT STARTED |
| Q.4 | Browser console clean on all pages | NOT STARTED |
| Q.5 | Live URL verified end-to-end | NOT STARTED |

## Deliverables (submission)
| # | Deliverable | Status |
|---|---|---|
| D.1 | Round-1 design deck (if still required) | **BLOCKED** — pending answer H1 (was Round 1 submitted before 2 Nov?) |
| D.2 | Round-2 10-slide PPT | NOT STARTED |
| D.3 | Architecture diagram: data → features → model → agent → work order | IN PROGRESS — ASCII version in `TECHNICAL_ARCHITECTURE.md`; needs a polished graphic |
| D.4 | Demo walkthrough script | NOT STARTED |
| D.5 | README + TEST_REPORT + DEPLOYMENT_STATUS | IN PROGRESS — `data/README.md` done; root README pending |
