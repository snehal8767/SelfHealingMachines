"""Layer 3/4 persistence — the SQLite store shared by the pipeline and the API.

One command (:func:`sync_fleet`, or ``python -m pipeline.store``) runs the whole
closed loop without manual steps, as the brief requires:

    score fleet → triage agent → engine state → predictions → work orders → audit log

Design points worth knowing for the review:

* **Idempotent** — running sync twice never duplicates predictions or work
  orders. A partial unique index enforces *one active order per machine*; the
  agent appends to ``agent_log`` on every run, which is the audit trail.
* **Human overrides win** — once an operator resolves/dismisses an order, the
  agent will not re-open it on the next sync (the machine keeps its severity
  state, but the order stays settled until it is genuinely re-opened by a new
  *worse* severity).
* ``engines.true_rul`` holds the official NASA label because this benchmark has
  it. It is *offline ground truth for evaluation* — in a real fleet it would be
  NULL until the machine actually fails.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .predict import score_test_set
from .triage import SEVERITIES, summarise, triage, work_orders_for

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "shm.db"

SEVERITY_ORDER = "CASE severity WHEN 'CRITICAL' THEN 0 WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END"

SCHEMA = """
CREATE TABLE IF NOT EXISTS engines (
    engine_id     INTEGER NOT NULL,
    subset        TEXT    NOT NULL,
    cycle         INTEGER NOT NULL,
    predicted_rul REAL    NOT NULL,
    anomaly       REAL    NOT NULL,
    severity      TEXT    NOT NULL CHECK (severity IN ('CRITICAL','HIGH','MEDIUM','LOW')),
    rul_slope     REAL    NOT NULL DEFAULT 0,
    true_rul      INTEGER,
    updated_at    TEXT    NOT NULL,
    PRIMARY KEY (engine_id, subset)
);

CREATE TABLE IF NOT EXISTS predictions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    engine_id     INTEGER NOT NULL,
    subset        TEXT    NOT NULL,
    cycle         INTEGER NOT NULL,
    predicted_rul REAL    NOT NULL,
    anomaly       REAL    NOT NULL,
    created_at    TEXT    NOT NULL,
    UNIQUE (engine_id, subset, cycle)
);

CREATE TABLE IF NOT EXISTS work_orders (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    engine_id     INTEGER NOT NULL,
    subset        TEXT    NOT NULL,
    severity      TEXT    NOT NULL,
    reason        TEXT    NOT NULL,
    predicted_rul REAL    NOT NULL,
    anomaly       REAL    NOT NULL,
    rul_slope     REAL    NOT NULL,
    status        TEXT    NOT NULL CHECK (status IN ('OPEN','HUMAN_REVIEW','RESOLVED','DISMISSED')),
    resolution    TEXT,
    created_at    TEXT    NOT NULL,
    resolved_at   TEXT
);

-- at most ONE active (OPEN/HUMAN_REVIEW) order per machine
CREATE UNIQUE INDEX IF NOT EXISTS ux_work_orders_active
    ON work_orders (engine_id, subset)
    WHERE status IN ('OPEN','HUMAN_REVIEW');

CREATE TABLE IF NOT EXISTS agent_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    engine_id     INTEGER NOT NULL,
    subset        TEXT    NOT NULL,
    severity      TEXT    NOT NULL,
    action        TEXT    NOT NULL,
    reason        TEXT    NOT NULL,
    predicted_rul REAL    NOT NULL,
    anomaly       REAL    NOT NULL,
    rul_slope     REAL    NOT NULL,
    created_at    TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS model_runs (
    run_id           TEXT PRIMARY KEY,
    subset           TEXT    NOT NULL,
    production_model TEXT    NOT NULL,
    metrics_json     TEXT    NOT NULL,
    trained_at       TEXT    NOT NULL,
    is_production    INTEGER NOT NULL DEFAULT 0
);
"""


# --------------------------------------------------------------------------
# connection helpers
# --------------------------------------------------------------------------
def default_db_path() -> Path:
    """DB location — ``SHM_DB_PATH`` env var wins (tests point it at a tmp file)."""
    env = os.environ.get("SHM_DB_PATH")
    return Path(env) if env else DEFAULT_DB


def connect(db_path: Path | str | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db(db_path: Path | str | None = None) -> Path:
    path = Path(db_path) if db_path else default_db_path()
    with connect(path) as conn:
        conn.executescript(SCHEMA)
    return path


def reset_db(db_path: Path | str | None = None) -> Path:
    """Drop every table (tests / clean re-seed)."""
    path = Path(db_path) if db_path else default_db_path()
    with connect(path) as conn:
        for table in ("engines", "predictions", "work_orders", "agent_log", "model_runs"):
            conn.execute(f"DROP TABLE IF EXISTS {table}")
    return path


def is_empty(db_path: Path | str | None = None) -> bool:
    try:
        with connect(db_path) as conn:
            row = conn.execute("SELECT COUNT(*) AS n FROM engines").fetchone()
            return int(row["n"]) == 0
    except sqlite3.OperationalError:  # table missing → never initialised
        return True


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------
# the end-to-end sync (G2: no manual steps once data is provided)
# --------------------------------------------------------------------------
def sync_fleet(
    subset: str = "FD001",
    db_path: Path | str | None = None,
    model_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Score the fleet, run the agent, persist everything. Idempotent."""
    init_db(db_path)
    kwargs: dict[str, Any] = {"subset": subset}
    if model_dir is not None:
        kwargs["model_dir"] = model_dir
    scored = score_test_set(**kwargs)

    decisions = triage(scored["current"], full_rows=scored["rows"], window=5)
    orders = work_orders_for(decisions, subset=subset)
    now = _now()

    with connect(db_path) as conn:
        # 1) engine state (upsert)
        by_engine = {d.engine_id: d for d in decisions}
        for row in scored["current"].itertuples(index=False):
            d = by_engine[int(row.unit_id)]
            conn.execute(
                """INSERT INTO engines
                   (engine_id, subset, cycle, predicted_rul, anomaly, severity,
                    rul_slope, true_rul, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(engine_id, subset) DO UPDATE SET
                     cycle=excluded.cycle, predicted_rul=excluded.predicted_rul,
                     anomaly=excluded.anomaly, severity=excluded.severity,
                     rul_slope=excluded.rul_slope, true_rul=excluded.true_rul,
                     updated_at=excluded.updated_at""",
                (
                    int(row.unit_id), subset, int(row.cycle), float(row.predicted_rul),
                    float(row.anomaly), d.severity, d.rul_slope,
                    int(row.true_rul), now,
                ),
            )

        # 2) prediction history: replace this subset's series
        conn.execute("DELETE FROM predictions WHERE subset = ?", (subset,))
        conn.executemany(
            """INSERT OR REPLACE INTO predictions
               (engine_id, subset, cycle, predicted_rul, anomaly, created_at)
               VALUES (?,?,?,?,?,?)""",
            [
                (int(r.unit_id), subset, int(r.cycle), float(r.predicted_rul),
                 float(r.anomaly), now)
                for r in scored["rows"].itertuples(index=False)
            ],
        )

        # 3) work orders — never duplicate an active one, never re-open a settled one
        active = {
            r["engine_id"]
            for r in conn.execute(
                "SELECT engine_id FROM work_orders WHERE subset=? AND status IN ('OPEN','HUMAN_REVIEW')",
                (subset,),
            )
        }
        settled = {
            r["engine_id"]
            for r in conn.execute(
                "SELECT engine_id FROM work_orders WHERE subset=? AND status IN ('RESOLVED','DISMISSED')",
                (subset,),
            )
        }
        created: list[int] = []
        for o in orders:
            if o["engine_id"] in active:
                continue
            if o["engine_id"] in settled:
                # operator already ruled on this machine; only a *worse*
                # severity than what they settled re-opens the conversation
                prev = conn.execute(
                    """SELECT severity FROM work_orders
                       WHERE engine_id=? AND subset=? AND status IN ('RESOLVED','DISMISSED')
                       ORDER BY id DESC LIMIT 1""",
                    (o["engine_id"], subset),
                ).fetchone()
                rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
                if prev and rank[o["severity"]] >= rank[prev["severity"]]:
                    continue
            conn.execute(
                """INSERT INTO work_orders
                   (engine_id, subset, severity, reason, predicted_rul, anomaly,
                    rul_slope, status, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    o["engine_id"], subset, o["severity"], o["reason"],
                    o["predicted_rul"], o["anomaly"], o["rul_slope"], o["status"], now,
                ),
            )
            created.append(o["engine_id"])

        # 4) audit trail — every decision, every run
        conn.executemany(
            """INSERT INTO agent_log
               (engine_id, subset, severity, action, reason, predicted_rul,
                anomaly, rul_slope, created_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            [
                (d.engine_id, subset, d.severity, d.action, d.reason,
                 d.predicted_rul, d.anomaly, d.rul_slope, now)
                for d in decisions
            ],
        )

        # 5) model run mirror (the dashboard reads this when mlruns is ephemeral)
        meta = scored["meta"]
        run_id = f"{subset}:{meta['trained_at']}"
        metrics = {
            "validation": meta["metrics"],
            "test": scored["metrics"],
            "selection_metric": meta.get("selection_metric"),
        }
        conn.execute("UPDATE model_runs SET is_production = 0 WHERE subset = ?", (subset,))
        conn.execute(
            """INSERT INTO model_runs
               (run_id, subset, production_model, metrics_json, trained_at, is_production)
               VALUES (?,?,?,?,?,1)
               ON CONFLICT(run_id) DO UPDATE SET
                 metrics_json=excluded.metrics_json,
                 production_model=excluded.production_model,
                 is_production=1""",
            (run_id, subset, meta["production_model"], json.dumps(metrics), meta["trained_at"]),
        )

        order_counts = {
            "OPEN": conn.execute(
                "SELECT COUNT(*) n FROM work_orders WHERE subset=? AND status='OPEN'", (subset,)
            ).fetchone()["n"],
            "HUMAN_REVIEW": conn.execute(
                "SELECT COUNT(*) n FROM work_orders WHERE subset=? AND status='HUMAN_REVIEW'", (subset,)
            ).fetchone()["n"],
        }

    return {
        "subset": subset,
        "engines": len(scored["current"]),
        "prediction_rows": len(scored["rows"]),
        "severity": summarise(decisions),
        "work_orders_created": len(created),
        "work_orders_by_status": order_counts,
        "metrics": scored["metrics"],
        "run_id": run_id,
    }


# --------------------------------------------------------------------------
# queries (the API calls these)
# --------------------------------------------------------------------------
def fleet_summary(subset: str = "FD001", db_path: Path | str | None = None) -> dict[str, Any]:
    init_db(db_path)
    with connect(db_path) as conn:
        severity = {s: 0 for s in SEVERITIES}
        for r in conn.execute(
            "SELECT severity, COUNT(*) n FROM engines WHERE subset=? GROUP BY severity", (subset,)
        ):
            severity[r["severity"]] = r["n"]
        orders = {
            r["status"]: r["n"]
            for r in conn.execute(
                "SELECT status, COUNT(*) n FROM work_orders WHERE subset=? GROUP BY status",
                (subset,),
            )
        }
        engines = conn.execute(
            f"""SELECT engine_id, cycle, predicted_rul, anomaly, severity, rul_slope,
                       true_rul, updated_at
                FROM engines WHERE subset=?
                ORDER BY {SEVERITY_ORDER}, predicted_rul ASC""",
            (subset,),
        ).fetchall()
    return {
        "subset": subset,
        "total_engines": sum(severity.values()),
        "severity": severity,
        "work_orders": orders,
        "engines": [dict(e) for e in engines],
    }


def get_engine(engine_id: int, subset: str = "FD001", db_path: Path | str | None = None) -> dict[str, Any] | None:
    init_db(db_path)
    with connect(db_path) as conn:
        engine = conn.execute(
            "SELECT * FROM engines WHERE engine_id=? AND subset=?", (engine_id, subset)
        ).fetchone()
        if engine is None:
            return None
        history = conn.execute(
            """SELECT cycle, predicted_rul, anomaly FROM predictions
               WHERE engine_id=? AND subset=? ORDER BY cycle""",
            (engine_id, subset),
        ).fetchall()
        orders = conn.execute(
            """SELECT * FROM work_orders WHERE engine_id=? AND subset=? ORDER BY id DESC""",
            (engine_id, subset),
        ).fetchall()
        log = conn.execute(
            """SELECT severity, action, reason, created_at FROM agent_log
               WHERE engine_id=? AND subset=? ORDER BY id DESC LIMIT 20""",
            (engine_id, subset),
        ).fetchall()
    return {
        "engine": dict(engine),
        "history": [dict(h) for h in history],
        "work_orders": [dict(o) for o in orders],
        "agent_log": [dict(l) for l in log],
    }


def list_work_orders(
    subset: str = "FD001",
    status: str | None = None,
    active_only: bool = False,
    db_path: Path | str | None = None,
) -> list[dict[str, Any]]:
    init_db(db_path)
    clauses = ["subset = ?"]
    params: list[Any] = [subset]
    if status:
        clauses.append("status = ?")
        params.append(status)
    elif active_only:
        clauses.append("status IN ('OPEN','HUMAN_REVIEW')")
    sql = (
        f"SELECT * FROM work_orders WHERE {' AND '.join(clauses)} "
        f"ORDER BY {SEVERITY_ORDER}, id DESC"
    )
    with connect(db_path) as conn:
        rows = conn.execute(sql, params).fetchall()
    return _rows(rows)


def resolve_work_order(
    order_id: int,
    resolution_status: str,
    note: str = "",
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Human exception handling — RESOLVED (fixed) or DISMISSED (false alarm)."""
    if resolution_status not in ("RESOLVED", "DISMISSED"):
        raise ValueError("resolution_status must be RESOLVED or DISMISSED")
    with connect(db_path) as conn:
        row = conn.execute("SELECT * FROM work_orders WHERE id=?", (order_id,)).fetchone()
        if row is None:
            raise KeyError(f"work order {order_id} not found")
        if row["status"] in ("RESOLVED", "DISMISSED"):
            raise ValueError(f"work order {order_id} is already {row['status']}")
        now = _now()
        conn.execute(
            "UPDATE work_orders SET status=?, resolution=?, resolved_at=? WHERE id=?",
            (resolution_status, note or None, now, order_id),
        )
        updated = conn.execute("SELECT * FROM work_orders WHERE id=?", (order_id,)).fetchone()
    return dict(updated)


def list_model_runs(subset: str = "FD001", db_path: Path | str | None = None) -> dict[str, Any]:
    init_db(db_path)
    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM model_runs WHERE subset=? ORDER BY trained_at DESC", (subset,)
        ).fetchall()
    runs = []
    for r in rows:
        item = dict(r)
        item["metrics"] = json.loads(item.pop("metrics_json"))
        item["is_production"] = bool(item["is_production"])
        runs.append(item)
    return {"subset": subset, "runs": runs}


def agent_activity(subset: str = "FD001", limit: int = 50, db_path: Path | str | None = None) -> list[dict[str, Any]]:
    with connect(db_path) as conn:
        rows = conn.execute(
            """SELECT * FROM agent_log WHERE subset=? ORDER BY id DESC LIMIT ?""",
            (subset, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def _rows(rows: Iterable[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(r) for r in rows]


if __name__ == "__main__":  # pragma: no cover - manual entry point
    print(json.dumps(sync_fleet(), indent=2))
