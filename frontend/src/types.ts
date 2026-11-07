export type Severity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
export type OrderStatus = "OPEN" | "HUMAN_REVIEW" | "RESOLVED" | "DISMISSED";

export interface EngineRow {
  engine_id: number;
  cycle: number;
  predicted_rul: number;
  anomaly: number;
  severity: Severity;
  rul_slope: number;
  true_rul: number | null;
  updated_at: string;
}

export interface FleetKPIs {
  avg_predicted_rul: number;
  median_predicted_rul: number;
  critical_share: number;
  open_orders: number;
}

export interface FleetResponse {
  subset: string;
  total_engines: number;
  severity: Record<Severity, number>;
  work_orders: Partial<Record<OrderStatus, number>>;
  kpis: FleetKPIs;
  engines: EngineRow[];
}

export interface HistoryPoint {
  cycle: number;
  predicted_rul: number;
  anomaly: number;
}

export interface WorkOrder {
  id: number;
  engine_id: number;
  subset: string;
  severity: Severity;
  reason: string;
  predicted_rul: number;
  anomaly: number;
  rul_slope: number;
  status: OrderStatus;
  resolution: string | null;
  created_at: string;
  resolved_at: string | null;
}

export interface AgentLogEntry {
  severity: Severity;
  action: string;
  reason: string;
  created_at: string;
  engine_id?: number | null;
}

export interface EngineDetailResponse {
  engine: EngineRow;
  history: HistoryPoint[];
  work_orders: WorkOrder[];
  agent_log: AgentLogEntry[];
}

export interface ModelMetrics {
  rmse: number;
  mae: number;
  phm_score: number;
  critical_recall: number;
  n_rows: number;
}

export interface ProductionMeta {
  subset: string;
  window: number;
  production_model: string;
  selection_metric: string;
  trained_at: string;
  metrics: Record<string, ModelMetrics>;
  feature_columns: string[];
  rul_clip: number;
}

export interface ModelRun {
  run_id: string;
  subset: string;
  production_model: string;
  metrics: {
    validation?: Record<string, ModelMetrics>;
    test?: ModelMetrics;
    selection_metric?: string;
  };
  trained_at: string;
  is_production: boolean;
}

export interface ModelsResponse {
  subset: string;
  production: ProductionMeta | null;
  runs: ModelRun[];
}

export interface MonitoringResponse {
  subset: string;
  severity: Record<Severity, number>;
  rul_bands: Record<string, number>;
  activity: AgentLogEntry[];
  runs: ModelRun[];
}

export type RetrainState = "QUEUED" | "RUNNING" | "DONE" | "ERROR";

export interface RetrainStatus {
  job_id: string;
  status: RetrainState;
  subset: string;
  started_at: string;
  finished_at: string | null;
  message: string | null;
  metrics: Record<string, unknown> | null;
}

export interface AboutResponse {
  project: string;
  dataset: Record<string, string | number>;
  architecture: string[];
  models: {
    production_model: string | null;
    trained_at: string | null;
    selection_metric: string | null;
    metrics: Record<string, ModelMetrics> | null;
  };
  limitations: string[];
}

export interface HealthResponse {
  status: "ok" | "degraded";
  subset: string;
  db_ready: boolean;
  engines: number;
  /** False means the server has no owner key, so writes return 503. */
  owner_configured?: boolean;
}
