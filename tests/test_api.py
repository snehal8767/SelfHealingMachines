"""Integration tests for the FastAPI layer.

Each test gets a private copy of the seeded SQLite store, so resolving a work
order in one test cannot leak into another. Tests skip when the pipeline has
not been run yet (``python -m pipeline.store``).
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import config
from backend.app.main import app

ROOT = Path(__file__).resolve().parents[1]
SEED_DB = ROOT / "data" / "shm.db"
DB_READY = SEED_DB.exists()


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    if not DB_READY:
        pytest.skip("seeded data/shm.db not found — run python -m pipeline.store")
    db = tmp_path / "shm.db"
    shutil.copy(SEED_DB, db)
    monkeypatch.setenv("SHM_DB_PATH", str(db))
    monkeypatch.setattr(config, "DB_PATH", db)
    monkeypatch.setattr(config, "API_TOKEN", "")
    return TestClient(app)


def test_health_reports_seeded_fleet(client: TestClient):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["db_ready"] is True
    assert body["engines"] == 100


def test_root_serves_landing_page_and_json(client: TestClient):
    page = client.get("/", headers={"Accept": "text/html"})
    assert page.status_code == 200
    assert page.headers["content-type"].startswith("text/html")
    assert "Self-Healing Machines API" in page.text
    assert "self-healing-machines.vercel.app" in page.text

    payload = client.get("/").json()
    assert payload["docs"] == "/docs"
    assert payload["health"] == "/api/health"


def test_fleet_shape_and_kpis(client: TestClient):
    response = client.get("/api/fleet")
    assert response.status_code == 200
    body = response.json()

    assert body["total_engines"] == 100
    assert len(body["engines"]) == 100
    assert sum(body["severity"].values()) == 100
    assert 0.0 <= body["kpis"]["critical_share"] <= 1.0
    assert body["kpis"]["median_predicted_rul"] >= 0


def test_engine_detail_and_unknown_engine(client: TestClient):
    detail = client.get("/api/engines/1")
    assert detail.status_code == 200
    body = detail.json()
    assert body["engine"]["engine_id"] == 1
    assert len(body["history"]) > 0
    assert body["history"][0]["cycle"] <= body["history"][-1]["cycle"]

    assert client.get("/api/engines/9999").status_code == 404


def test_work_orders_filters(client: TestClient):
    all_orders = client.get("/api/work-orders").json()
    active = client.get("/api/work-orders", params={"active_only": True}).json()
    review = client.get("/api/work-orders", params={"status": "HUMAN_REVIEW"}).json()

    assert len(all_orders) >= len(active)
    assert all(order["status"] in ("OPEN", "HUMAN_REVIEW") for order in active)
    assert all(order["status"] == "HUMAN_REVIEW" for order in review)


def test_resolve_work_order_then_conflict(client: TestClient):
    order = client.get("/api/work-orders", params={"status": "HUMAN_REVIEW"}).json()[0]

    resolved = client.post(
        f"/api/work-orders/{order['id']}/resolve",
        json={"status": "RESOLVED", "note": "Technician replaced the bearing"},
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "RESOLVED"
    assert resolved.json()["resolution"] == "Technician replaced the bearing"

    again = client.post(
        f"/api/work-orders/{order['id']}/resolve",
        json={"status": "DISMISSED"},
    )
    assert again.status_code == 409

    assert client.post("/api/work-orders/999999/resolve", json={"status": "RESOLVED"}).status_code == 404


def test_resolve_rejects_bad_status(client: TestClient):
    order = client.get("/api/work-orders").json()[0]
    response = client.post(
        f"/api/work-orders/{order['id']}/resolve", json={"status": "DONE"}
    )
    assert response.status_code == 422


def test_models_and_monitoring(client: TestClient):
    models = client.get("/api/models").json()
    assert models["runs"]
    assert models["production"]["production_model"] in ("baseline", "candidate")

    monitoring = client.get("/api/monitoring").json()
    assert sum(monitoring["rul_bands"].values()) == 100
    assert monitoring["activity"]


def test_about_has_dataset_provenance(client: TestClient):
    body = client.get("/api/about").json()
    assert "C-MAPSS" in body["dataset"]["name"]
    assert body["dataset"]["license"].startswith("Public domain")
    assert len(body["architecture"]) >= 5
    assert body["limitations"]


def test_retrain_unknown_job_is_404(client: TestClient):
    assert client.get("/api/retrain/does-not-exist").status_code == 404


def test_token_guard_on_mutations(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "API_TOKEN", "secret-token")
    order = client.get("/api/work-orders", params={"status": "HUMAN_REVIEW"}).json()[0]
    url = f"/api/work-orders/{order['id']}/resolve"

    assert client.post(url, json={"status": "RESOLVED"}).status_code == 401
    assert (
        client.post(url, json={"status": "RESOLVED"}, headers={"X-API-Token": "wrong"}).status_code
        == 401
    )
    assert (
        client.post(
            url, json={"status": "RESOLVED"}, headers={"X-API-Token": "secret-token"}
        ).status_code
        == 200
    )
