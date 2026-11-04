# FEATURE_CHECKLIST.md

Status legend: `NOT STARTED` · `IN PROGRESS` · `BLOCKED` · `IMPLEMENTED` · `TESTED` · `VERIFIED`

> A feature is **VERIFIED** only after it has been demonstrated working on the deployed URL —
> code existing is not enough.

---

## Layer 1 — Data Engineering
| # | Feature | Status |
|---|---|---|
| 1.1 | Load NASA C-MAPSS files (train/test/RUL) for chosen subset(s) | NOT STARTED |
| 1.2 | Schema validation + missing-value handling | NOT STARTED |
| 1.3 | Basic noise handling / per-engine normalisation | NOT STARTED |
| 1.4 | Rolling-window features (mean, std, slope) | NOT STARTED |
| 1.5 | RUL label construction (clipped, per-engine) | NOT STARTED |
| 1.6 | Reproducible, one-command feature build | NOT STARTED |

## Layer 2 — Machine Learning
| # | Feature | Status |
|---|---|---|
| 2.1 | Baseline RUL model (linear/ridge) | NOT STARTED |
| 2.2 | Primary RUL model (gradient boosting / RF) with reasoning | NOT STARTED |
| 2.3 | Anomaly detection (IsolationForest or equivalent) | NOT STARTED |
| 2.4 | Evaluation: RMSE, MAE, NASA PHM score, failure recall | NOT STARTED |
| 2.5 | Handles mild class imbalance deliberately | NOT STARTED |

## Layer 3 — MLOps
| # | Feature | Status |
|---|---|---|
| 3.1 | MLflow experiment tracking (params + metrics + artifacts) | NOT STARTED |
| 3.2 | Model versioning / production pointer | NOT STARTED |
| 3.3 | Retraining flow triggered by "new data" | NOT STARTED |
| 3.4 | Monitoring view (metric trends, RUL distribution, drift signal) | NOT STARTED |

## Layer 4 — Triage Agent (no LLM)
| # | Feature | Status |
|---|---|---|
| 4.1 | Rule engine: RUL + anomaly + trend → severity | NOT STARTED |
| 4.2 | Auto-create work order for CRITICAL/HIGH | NOT STARTED |
| 4.3 | Human exception queue for MEDIUM (approve/override/dismiss) | NOT STARTED |
| 4.4 | Full audit trail of agent decisions | NOT STARTED |

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
| Q.1 | pytest suite green | NOT STARTED |
| Q.2 | Production build + TypeScript checks pass | NOT STARTED |
| Q.3 | No fake buttons / dead links / hardcoded demo data presented as real | NOT STARTED |
| Q.4 | Browser console clean on all pages | NOT STARTED |
| Q.5 | Live URL verified end-to-end | NOT STARTED |

## Deliverables (submission)
| # | Deliverable | Status |
|---|---|---|
| D.1 | Round-1 design deck (if still required) | BLOCKED — pending answer H1 |
| D.2 | Round-2 10-slide PPT | NOT STARTED |
| D.3 | Architecture diagram: data → features → model → agent → work order | NOT STARTED |
| D.4 | Demo walkthrough script | NOT STARTED |
| D.5 | README + TEST_REPORT + DEPLOYMENT_STATUS | NOT STARTED |
