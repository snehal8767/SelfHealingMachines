"""FastAPI layer — thin, typed read API over the pipeline's SQLite store.

Design notes for the review:

* The API never re-implements ML logic. It calls the same ``pipeline.store``
  functions the CLI uses, so the dashboard cannot disagree with the pipeline.
* Reads are public. Writes (resolving a work order, retraining) require
  ``X-API-Token`` to match ``SHM_API_TOKEN``. This **fails closed**: when the
  server has no key configured, every write returns 503 instead of silently
  letting strangers mutate the demo.
* ``/api/retrain`` runs the real Layer-2 pipeline in a background thread and
  re-syncs the fleet, which is the "closed loop" the brief asks for. It needs
  the raw NASA files on disk; without them it returns 503 instead of pretending.
"""
from __future__ import annotations

import hmac
import json
import statistics
import sys
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:  # pragma: no cover - import-time bootstrapping
    sys.path.insert(0, str(ROOT))

from backend.app import config  # noqa: E402
from backend.app.schemas import (  # noqa: E402
    AboutResponse,
    EngineDetailResponse,
    FleetKPIs,
    FleetResponse,
    HealthResponse,
    ModelsResponse,
    MonitoringResponse,
    ResolveRequest,
    RetrainRequest,
    RetrainStatus,
    WorkOrder,
)
from pipeline import store  # noqa: E402
from pipeline.features import DEFAULT_WINDOW  # noqa: E402
from pipeline.ingest import RAW_DIR  # noqa: E402

app = FastAPI(
    title="Self-Healing Machines API",
    version="1.0.0",
    description="RUL prediction + rule-based triage for the NASA C-MAPSS fleet.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = APIRouter(prefix="/api")


def require_token(x_api_token: str | None = Header(default=None)) -> None:
    """Owner-only guard for every mutation.

    Fails closed: an unconfigured server refuses writes (503) rather than
    exposing them. The comparison is constant-time to avoid timing oracles.
    """
    if not config.API_TOKEN:
        raise HTTPException(
            status_code=503,
            detail="Owner key is not configured on the server (set SHM_API_TOKEN). Writes are disabled.",
        )
    if not x_api_token or not hmac.compare_digest(x_api_token, config.API_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Token")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------
# owner access — lets the UI check a pasted key before storing it
# --------------------------------------------------------------------------
@api.post("/admin/verify")
def admin_verify(_: None = Depends(require_token)) -> dict[str, bool]:
    return {"ok": True}


# --------------------------------------------------------------------------
# health / fleet
# --------------------------------------------------------------------------
DASHBOARD_URL = "https://self-healing-machines.vercel.app"

_LANDING_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Self-Healing Machines API</title>
<style>
  :root {{ color-scheme: dark; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; min-height:100vh; display:flex; align-items:center; justify-content:center;
         padding:32px; background:#09090b; color:#e4e4e7;
         font-family:ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }}
  main {{ width:100%; max-width:720px; }}
  .badge {{ display:inline-flex; align-items:center; gap:8px; padding:6px 12px; border-radius:999px;
           font-size:12px; color:#fbbf24; background:rgba(251,191,36,.08);
           border:1px solid rgba(251,191,36,.25); }}
  .dot {{ width:7px; height:7px; border-radius:50%; background:#34d399; }}
  h1 {{ margin:20px 0 10px; font-size:30px; line-height:1.15; letter-spacing:-.02em; }}
  p.lead {{ margin:0 0 28px; max-width:60ch; font-size:14px; line-height:1.65; color:#a1a1aa; }}
  .grid {{ display:grid; gap:12px; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); }}
  a.card {{ display:block; padding:16px 18px; border:1px solid #27272a; border-radius:12px;
           background:#111113; color:inherit; text-decoration:none;
           transition:border-color .15s, transform .15s; }}
  a.card:hover {{ border-color:#52525b; transform:translateY(-1px); }}
  .k {{ font-size:13px; font-weight:600; color:#fafafa; }}
  .v {{ margin-top:4px; font-size:12px; color:#71717a; }}
  footer {{ margin-top:28px; font-size:11.5px; line-height:1.6; color:#52525b; }}
</style>
</head>
<body>
<main>
  <span class="badge"><span class="dot"></span> API online &middot; FD001</span>
  <h1>Self-Healing Machines API</h1>
  <p class="lead">RUL prediction and deterministic work-order triage for the NASA C-MAPSS fleet.
     No LLM in the runtime path &mdash; every decision is a documented threshold.</p>
  <div class="grid">
    <a class="card" href="{dashboard}"><div class="k">Dashboard &rarr;</div><div class="v">Fleet, work orders, models</div></a>
    <a class="card" href="/docs"><div class="k">API docs &rarr;</div><div class="v">Swagger &middot; 9 endpoints</div></a>
    <a class="card" href="/api/health"><div class="k">Health</div><div class="v">/api/health</div></a>
    <a class="card" href="/api/fleet"><div class="k">Fleet JSON</div><div class="v">/api/fleet</div></a>
  </div>
  <footer>Benchmark results on simulated engines, not operational advice.
          Dataset: NASA C-MAPSS (public domain).</footer>
</main>
</body>
</html>
""".format(dashboard=DASHBOARD_URL)


@app.get("/", include_in_schema=False)
def root(request: Request) -> Any:
    """Browser-friendly landing page; plain JSON for API clients."""
    if "text/html" in request.headers.get("accept", ""):
        return HTMLResponse(_LANDING_PAGE)
    return {
        "service": "Self-Healing Machines API",
        "docs": "/docs",
        "health": "/api/health",
        "dashboard": DASHBOARD_URL,
    }


@api.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    db_ready = config.DB_PATH.exists()
    engines = 0
    if db_ready:
        try:
            engines = len(store.fleet_summary(config.SUBSET)["engines"])
        except Exception:  # uninitialised or unreadable DB
            db_ready = False
    return HealthResponse(
        status="ok" if db_ready and engines else "degraded",
        subset=config.SUBSET,
        db_ready=db_ready,
        engines=engines,
        owner_configured=bool(config.API_TOKEN),
    )


@app.get("/health", include_in_schema=False)
def health_alias() -> HealthResponse:
    """Convenience alias so ``/health`` never returns a confusing 404."""
    return health()


@api.get("/fleet", response_model=FleetResponse)
def fleet(subset: str = Query(default=config.SUBSET, max_length=8)) -> FleetResponse:
    try:
        summary = store.fleet_summary(subset)
    except Exception as exc:  # uninitialised DB should be a clear 503, not a 500
        raise HTTPException(status_code=503, detail=f"Fleet store unavailable: {exc}") from exc

    engines = summary["engines"]
    if not engines:
        raise HTTPException(
            status_code=404,
            detail=f"No fleet data for {subset}. Run: python -m pipeline.store --subset {subset}",
        )

    ruls = [e["predicted_rul"] for e in engines]
    kpis = FleetKPIs(
        avg_predicted_rul=round(float(statistics.fmean(ruls)), 1),
        median_predicted_rul=round(float(statistics.median(ruls)), 1),
        critical_share=round(summary["severity"].get("CRITICAL", 0) / len(engines), 3),
        open_orders=int(summary["work_orders"].get("OPEN", 0)),
    )
    return FleetResponse(**summary, kpis=kpis)


@api.get("/engines/{engine_id}", response_model=EngineDetailResponse)
def engine(engine_id: int, subset: str = Query(default=config.SUBSET, max_length=8)) -> EngineDetailResponse:
    detail = store.get_engine(engine_id, subset)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Engine {engine_id} not found in {subset}")
    return EngineDetailResponse(**detail)


# --------------------------------------------------------------------------
# work orders — the human exception queue
# --------------------------------------------------------------------------
@api.get("/work-orders", response_model=list[WorkOrder])
def work_orders(
    subset: str = Query(default=config.SUBSET, max_length=8),
    status: str | None = Query(default=None, pattern="^(OPEN|HUMAN_REVIEW|RESOLVED|DISMISSED)$"),
    active_only: bool = Query(default=False),
) -> list[WorkOrder]:
    return [WorkOrder(**row) for row in store.list_work_orders(subset, status, active_only)]


@api.post("/work-orders/{order_id}/resolve", response_model=WorkOrder)
def resolve(
    order_id: int,
    body: ResolveRequest,
    _: None = Depends(require_token),
) -> WorkOrder:
    try:
        updated = store.resolve_work_order(order_id, body.status, body.note)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return WorkOrder(**updated)


# --------------------------------------------------------------------------
# models / monitoring
# --------------------------------------------------------------------------
def _production_meta() -> dict[str, Any] | None:
    path = config.MODELS_DIR / "production.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


@api.get("/models", response_model=ModelsResponse)
def models(subset: str = Query(default=config.SUBSET, max_length=8)) -> ModelsResponse:
    return ModelsResponse(**store.list_model_runs(subset), production=_production_meta())


@api.get("/monitoring", response_model=MonitoringResponse)
def monitoring(
    subset: str = Query(default=config.SUBSET, max_length=8),
    limit: int = Query(default=30, ge=1, le=200),
) -> MonitoringResponse:
    summary = store.fleet_summary(subset)
    bands = {"0-15": 0, "16-30": 0, "31-60": 0, "61-125": 0, "125+": 0}
    for row in summary["engines"]:
        rul = float(row["predicted_rul"])
        if rul <= 15:
            bands["0-15"] += 1
        elif rul <= 30:
            bands["16-30"] += 1
        elif rul <= 60:
            bands["31-60"] += 1
        elif rul <= 125:
            bands["61-125"] += 1
        else:
            bands["125+"] += 1
    runs = store.list_model_runs(subset)["runs"]
    return MonitoringResponse(
        subset=subset,
        severity=summary["severity"],
        rul_bands=bands,
        activity=store.agent_activity(subset, limit=limit),
        runs=runs,
    )


# --------------------------------------------------------------------------
# the closed loop: retrain → new model version → re-score → new work orders
# --------------------------------------------------------------------------
_jobs: dict[str, RetrainStatus] = {}
_lock = threading.Lock()


def _worker(job_id: str, subset: str, window: int) -> None:
    from pipeline.store import sync_fleet
    from pipeline.train import train_subset

    with _lock:
        _jobs[job_id] = _jobs[job_id].model_copy(update={"status": "RUNNING"})
    try:
        result = train_subset(subset=subset, window=window, log_mlflow=False)
        sync = sync_fleet(subset=subset)
        metrics = {
            "validation": result["metrics"],
            "test": sync["metrics"],
            "production_model": result["production_model"],
        }
        with _lock:
            _jobs[job_id] = _jobs[job_id].model_copy(
                update={
                    "status": "DONE",
                    "finished_at": _now(),
                    "message": f"New {subset} model version promoted and fleet re-scored.",
                    "metrics": metrics,
                }
            )
    except Exception as exc:  # surfaced to the UI, never swallowed silently
        with _lock:
            _jobs[job_id] = _jobs[job_id].model_copy(
                update={"status": "ERROR", "finished_at": _now(), "message": str(exc)[:500]}
            )


@api.post("/retrain", status_code=202, response_model=RetrainStatus)
def retrain(
    body: RetrainRequest,
    _: None = Depends(require_token),
) -> RetrainStatus:
    subset = (body.subset or config.SUBSET).upper()
    needed = [RAW_DIR / f"train_{subset}.txt", RAW_DIR / f"test_{subset}.txt", RAW_DIR / f"RUL_{subset}.txt"]
    missing = [p.name for p in needed if not p.exists()]
    if missing:
        raise HTTPException(
            status_code=503,
            detail=f"Raw data missing for retraining: {missing}. See data/README.md.",
        )

    with _lock:
        if any(job.status in ("QUEUED", "RUNNING") for job in _jobs.values()):
            raise HTTPException(status_code=409, detail="A retraining job is already running")
        job_id = uuid.uuid4().hex[:12]
        _jobs[job_id] = RetrainStatus(
            job_id=job_id,
            status="QUEUED",
            subset=subset,
            started_at=_now(),
        )
    threading.Thread(
        target=_worker,
        args=(job_id, subset, body.window or DEFAULT_WINDOW),
        daemon=True,
    ).start()
    return _jobs[job_id]


@api.get("/retrain/{job_id}", response_model=RetrainStatus)
def retrain_status(job_id: str) -> RetrainStatus:
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Unknown retraining job {job_id}")
    return job


# --------------------------------------------------------------------------
# about — the page judges land on
# --------------------------------------------------------------------------
@api.get("/about", response_model=AboutResponse)
def about() -> AboutResponse:
    meta = _production_meta()
    return AboutResponse(
        project="Self-Healing Machines — Predictive Maintenance for a Connected Fleet",
        dataset=config.DATASET,
        architecture=[
            "NASA C-MAPSS raw files → validated ingestion",
            "Per-engine cleaning + rolling mean/std/trend features",
            "RUL regression (Ridge baseline vs HistGradientBoosting) + IsolationForest anomaly detector",
            "Rule-based triage agent (no LLM): RUL + anomaly + trend → severity",
            "CRITICAL/HIGH → automatic work order; MEDIUM → human exception queue",
            "FastAPI + SQLite → React dashboard, retrain re-scores the whole fleet",
        ],
        models={
            "production_model": (meta or {}).get("production_model"),
            "trained_at": (meta or {}).get("trained_at"),
            "selection_metric": (meta or {}).get("selection_metric"),
            "metrics": (meta or {}).get("metrics"),
        },
        limitations=[
            "Benchmark data is simulated; real fleets need per-asset calibration.",
            "RUL labels are capped at 125 cycles, so long-horizon claims are out of scope.",
            "The free hosting tier has an ephemeral disk: writes reset on redeploy.",
            "Work-order resolution is a prototype workflow, not an ERP integration.",
        ],
    )


app.include_router(api)
