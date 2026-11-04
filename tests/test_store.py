"""Tests for the SQLite store — schema, idempotent sync, dedup, human overrides."""
import os
from pathlib import Path

import pytest

from pipeline.predict import score_test_set
from pipeline.store import (
    connect,
    get_engine,
    init_db,
    is_empty,
    list_model_runs,
    list_work_orders,
    reset_db,
    resolve_work_order,
    sync_fleet,
)

DATA_READY = Path("data/raw/train_FD001.txt").exists() and Path("models/production.json").exists()
pytestmark = pytest.mark.skipif(not DATA_READY, reason="needs NASA data + trained model")


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    db = tmp_path / "shm.db"
    monkeypatch.setenv("SHM_DB_PATH", str(db))
    reset_db(db)
    return db


def test_init_creates_all_tables(tmp_db):
    init_db(tmp_db)
    with connect(tmp_db) as c:
        tables = {r[0] for r in c.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
    assert {"engines", "predictions", "work_orders", "agent_log", "model_runs"} <= tables


def test_empty_db_is_empty(tmp_db):
    assert is_empty(tmp_db) is True


def test_sync_populates_fleet_and_is_idempotent(tmp_db):
    first = sync_fleet(db_path=tmp_db)
    assert first["engines"] == 100
    assert first["prediction_rows"] == len(score_test_set()["rows"])
    assert first["work_orders_created"] == len(first["severity"]) - first["severity"]["LOW"]
    assert is_empty(tmp_db) is False

    # second sync: no duplicate predictions, no duplicate active work orders
    pred_before = _count(tmp_db, "predictions")
    orders_before = _count(tmp_db, "work_orders")
    second = sync_fleet(db_path=tmp_db)
    assert _count(tmp_db, "predictions") == pred_before
    assert _count(tmp_db, "work_orders") == orders_before
    assert second["work_orders_created"] == 0


def test_sync_severity_matches_triage(tmp_db):
    from pipeline.triage import summarise, triage

    result = sync_fleet(db_path=tmp_db)
    assert result["severity"] == {"CRITICAL": 14, "HIGH": 10, "MEDIUM": 18, "LOW": 58}

    with connect(tmp_db) as c:
        counts = {r["severity"]: r["n"] for r in c.execute(
            "SELECT severity, COUNT(*) n FROM engines GROUP BY severity"
        ).fetchall()}
    assert counts == result["severity"]


def test_one_active_order_per_engine(tmp_db):
    sync_fleet(db_path=tmp_db)
    with connect(tmp_db) as c:
        dupes = c.execute(
            """SELECT engine_id, COUNT(*) n FROM work_orders
               WHERE status IN ('OPEN','HUMAN_REVIEW') GROUP BY engine_id HAVING n>1"""
        ).fetchall()
    assert dupes == []


def test_human_override_is_not_reopened(tmp_db):
    sync_fleet(db_path=tmp_db)
    # resolve the first open order as RESOLVED
    orders = list_work_orders(db_path=tmp_db, active_only=True)
    assert orders
    target = orders[0]
    resolve_work_order(target["id"], "RESOLVED", "fixed in field", db_path=tmp_db)

    # re-sync must NOT reopen it
    sync_fleet(db_path=tmp_db)
    row = next(o for o in list_work_orders(db_path=tmp_db) if o["id"] == target["id"])
    assert row["status"] == "RESOLVED"
    assert row["resolution"] == "fixed in field"


def test_resolve_rejects_double_resolve_and_bad_status(tmp_db):
    sync_fleet(db_path=tmp_db)
    order = list_work_orders(db_path=tmp_db, active_only=True)[0]
    resolve_work_order(order["id"], "DISMISSED", db_path=tmp_db)
    with pytest.raises(ValueError):
        resolve_work_order(order["id"], "RESOLVED", db_path=tmp_db)
    with pytest.raises(ValueError):
        resolve_work_order(order["id"], "OPEN", db_path=tmp_db)
    with pytest.raises(KeyError):
        resolve_work_order(999999, "RESOLVED", db_path=tmp_db)


def test_get_engine_returns_history_and_orders(tmp_db):
    sync_fleet(db_path=tmp_db)
    detail = get_engine(1, db_path=tmp_db)
    assert detail is not None
    assert detail["engine"]["engine_id"] == 1
    assert len(detail["history"]) > 0
    assert all(h["cycle"] <= detail["engine"]["cycle"] for h in detail["history"])
    assert get_engine(9999, db_path=tmp_db) is None


def test_model_runs_mirror_production(tmp_db):
    sync_fleet(db_path=tmp_db)
    data = list_model_runs(db_path=tmp_db)
    assert data["runs"]
    run = data["runs"][0]
    assert run["is_production"] is True
    assert run["production_model"] in ("baseline", "candidate")
    assert run["metrics"]["validation"]["candidate"]["rmse"] < run["metrics"]["validation"]["baseline"]["rmse"]


def _count(db, table):
    with connect(db) as c:
        return c.execute(f"SELECT COUNT(*) n FROM {table}").fetchone()["n"]
