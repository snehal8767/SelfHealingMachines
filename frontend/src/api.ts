import type {
  AboutResponse,
  EngineDetailResponse,
  FleetResponse,
  HealthResponse,
  ModelsResponse,
  MonitoringResponse,
  RetrainStatus,
  WorkOrder,
} from "./types";

export const API_URL = (
  (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000"
).replace(/\/$/, "");

const TOKEN = (import.meta.env.VITE_API_TOKEN as string | undefined) ?? "";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(TOKEN ? { "X-API-Token": TOKEN } : {}),
        ...(init?.headers ?? {}),
      },
    });
  } catch {
    throw new ApiError(
      0,
      `Cannot reach the API at ${API_URL}. Start it with: uvicorn backend.app.main:app --reload`,
    );
  }

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as { detail?: unknown };
      detail =
        typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    } catch {
      /* non-JSON error body — keep the status text */
    }
    throw new ApiError(response.status, detail);
  }

  return (await response.json()) as T;
}

export const api = {
  health: () => request<HealthResponse>("/api/health"),
  fleet: () => request<FleetResponse>("/api/fleet"),
  engine: (id: number) => request<EngineDetailResponse>(`/api/engines/${id}`),
  workOrders: (params?: { status?: string; activeOnly?: boolean }) => {
    const query = new URLSearchParams();
    if (params?.status) query.set("status", params.status);
    if (params?.activeOnly) query.set("active_only", "true");
    const suffix = query.toString() ? `?${query}` : "";
    return request<WorkOrder[]>(`/api/work-orders${suffix}`);
  },
  resolve: (id: number, status: "RESOLVED" | "DISMISSED", note = "") =>
    request<WorkOrder>(`/api/work-orders/${id}/resolve`, {
      method: "POST",
      body: JSON.stringify({ status, note }),
    }),
  models: () => request<ModelsResponse>("/api/models"),
  monitoring: () => request<MonitoringResponse>("/api/monitoring"),
  retrain: () =>
    request<RetrainStatus>("/api/retrain", {
      method: "POST",
      body: JSON.stringify({}),
    }),
  retrainStatus: (jobId: string) => request<RetrainStatus>(`/api/retrain/${jobId}`),
  about: () => request<AboutResponse>("/api/about"),
};
