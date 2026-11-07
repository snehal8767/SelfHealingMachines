"""Response contracts for the API (validated on the way out, documented in /docs)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class EngineRow(BaseModel):
    engine_id: int
    cycle: int
    predicted_rul: float
    anomaly: float
    severity: str
    rul_slope: float
    true_rul: int | None = None
    updated_at: str


class FleetKPIs(BaseModel):
    avg_predicted_rul: float
    median_predicted_rul: float
    critical_share: float = Field(description="Share of engines in CRITICAL severity, 0-1")
    open_orders: int


class FleetResponse(BaseModel):
    subset: str
    total_engines: int
    severity: dict[str, int]
    work_orders: dict[str, int]
    kpis: FleetKPIs
    engines: list[EngineRow]


class HistoryPoint(BaseModel):
    cycle: int
    predicted_rul: float
    anomaly: float


class WorkOrder(BaseModel):
    id: int
    engine_id: int
    subset: str
    severity: str
    reason: str
    predicted_rul: float
    anomaly: float
    rul_slope: float
    status: str
    resolution: str | None = None
    created_at: str
    resolved_at: str | None = None


class AgentLogEntry(BaseModel):
    severity: str
    action: str
    reason: str
    created_at: str
    engine_id: int | None = None


class EngineDetailResponse(BaseModel):
    engine: EngineRow
    history: list[HistoryPoint]
    work_orders: list[WorkOrder]
    agent_log: list[AgentLogEntry]


class ResolveRequest(BaseModel):
    status: Literal["RESOLVED", "DISMISSED"]
    note: str = ""


class ModelRun(BaseModel):
    run_id: str
    subset: str
    production_model: str
    metrics: dict[str, Any]
    trained_at: str
    is_production: bool


class ModelsResponse(BaseModel):
    subset: str
    production: dict[str, Any] | None
    runs: list[ModelRun]


class MonitoringResponse(BaseModel):
    subset: str
    severity: dict[str, int]
    rul_bands: dict[str, int]
    activity: list[AgentLogEntry]
    runs: list[ModelRun]


class RetrainRequest(BaseModel):
    subset: str | None = None
    window: int = Field(default=5, ge=1, le=50)


class RetrainStatus(BaseModel):
    job_id: str
    status: Literal["QUEUED", "RUNNING", "DONE", "ERROR"]
    subset: str
    started_at: str
    finished_at: str | None = None
    message: str | None = None
    metrics: dict[str, Any] | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    subset: str
    db_ready: bool
    engines: int
    #: False means the server has no SHM_API_TOKEN, so writes return 503.
    owner_configured: bool = False


class AboutResponse(BaseModel):
    project: str
    dataset: dict[str, Any]
    architecture: list[str]
    models: dict[str, Any]
    limitations: list[str]
