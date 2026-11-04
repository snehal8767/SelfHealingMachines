import { Link, useParams } from "react-router-dom";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api";
import { useApi } from "../hooks/useApi";
import { Panel, StatCard } from "../components/Panel";
import { SeverityBadge } from "../components/SeverityBadge";
import { ErrorBlock, LoadingBlock } from "../components/StateViews";
import { ArrowLeftIcon } from "../components/icons";
import { fmtDateTime, fmtNumber, fmtPct, timeAgo } from "../lib/format";

export function EngineDetail() {
  const { id } = useParams();
  const engineId = Number(id);
  const { data, error, loading, reload } = useApi(() => api.engine(engineId), [engineId]);

  if (loading && !data) {
    return (
      <Panel title={`Engine #${id}`}>
        <LoadingBlock rows={5} />
      </Panel>
    );
  }

  if (error) {
    return (
      <Panel title={`Engine #${id}`}>
        <ErrorBlock message={error} onRetry={reload} />
      </Panel>
    );
  }

  if (!data) return null;

  const { engine, history, work_orders, agent_log } = data;

  return (
    <div className="space-y-6">
      <div>
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-zinc-400 transition hover:text-zinc-100"
        >
          <ArrowLeftIcon className="h-3.5 w-3.5" />
          Back to fleet
        </Link>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <h1 className="text-xl font-semibold tracking-tight text-zinc-100 sm:text-2xl">
            Engine #{engine.engine_id}
          </h1>
          <SeverityBadge severity={engine.severity} size="md" />
        </div>
        <p className="mt-1 text-sm text-zinc-400">
          Last observation at cycle {engine.cycle} · scored {timeAgo(engine.updated_at)}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <StatCard
          label="Predicted RUL"
          value={`${fmtNumber(engine.predicted_rul)}c`}
          hint={engine.true_rul != null ? `true: ${engine.true_rul}c (offline)` : "operational estimate"}
          tone={engine.predicted_rul <= 15 ? "danger" : engine.predicted_rul <= 30 ? "warning" : "success"}
        />
        <StatCard
          label="Anomaly percentile"
          value={fmtPct(engine.anomaly, 1)}
          hint="1.0 = more abnormal than every healthy reading"
        />
        <StatCard
          label="RUL trend"
          value={`${engine.rul_slope.toFixed(2)}c/cy`}
          hint="life lost per cycle over the recent window"
          tone={engine.rul_slope < -1.5 ? "danger" : "neutral"}
        />
        <StatCard
          label="Open orders"
          value={work_orders.filter((o) => o.status === "OPEN" || o.status === "HUMAN_REVIEW").length}
          hint={`${work_orders.length} total on record`}
          tone="warning"
        />
      </div>

      <Panel
        title="Life left over time"
        subtitle="Green: predicted RUL per cycle. Amber: anomaly percentile (right axis)."
      >
        <div className="px-2 py-4 sm:px-4">
          <ResponsiveContainer width="100%" height={320}>
            <ComposedChart data={history} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
              <defs>
                <linearGradient id="anomalyFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#f59e0b" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#f59e0b" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="rgba(255,255,255,0.05)" vertical={false} />
              <XAxis dataKey="cycle" tickLine={false} axisLine={false} minTickGap={28} />
              <YAxis yAxisId="rul" tickLine={false} axisLine={false} width={44} />
              <YAxis
                yAxisId="anomaly"
                orientation="right"
                domain={[0, 1]}
                tickFormatter={(value: number) => `${Math.round(value * 100)}%`}
                tickLine={false}
                axisLine={false}
                width={48}
              />
              <Tooltip
                contentStyle={{
                  background: "#131316",
                  border: "1px solid rgba(255,255,255,0.08)",
                  borderRadius: 10,
                  fontSize: 12,
                }}
                labelStyle={{ color: "#a1a1aa" }}
              />
              <Area
                yAxisId="anomaly"
                type="monotone"
                dataKey="anomaly"
                name="Anomaly"
                stroke="#f59e0b"
                strokeWidth={1.2}
                fill="url(#anomalyFill)"
              />
              <Line
                yAxisId="rul"
                type="monotone"
                dataKey="predicted_rul"
                name="Predicted RUL"
                stroke="#34d399"
                strokeWidth={2}
                dot={false}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </Panel>

      <div className="grid gap-6 xl:grid-cols-2">
        <Panel title="Work orders" subtitle="Agent-created, newest first">
          {work_orders.length === 0 ? (
            <p className="px-5 py-8 text-center text-sm text-zinc-500">
              No work order has ever been raised for this machine.
            </p>
          ) : (
            <ul className="divide-y divide-white/5">
              {work_orders.map((order) => (
                <li key={order.id} className="px-5 py-3.5">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <SeverityBadge severity={order.severity} />
                      <span className="text-xs text-zinc-500">#{order.id}</span>
                    </div>
                    <span className="rounded-full border border-white/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-zinc-400">
                      {order.status.replace("_", " ")}
                    </span>
                  </div>
                  <p className="mt-2 text-xs leading-relaxed text-zinc-400">{order.reason}</p>
                  <p className="mt-1.5 text-[11px] text-zinc-600">
                    RUL {fmtNumber(order.predicted_rul)}c · anomaly {fmtPct(order.anomaly, 1)} ·{" "}
                    {fmtDateTime(order.created_at)}
                  </p>
                  {order.resolution ? (
                    <p className="mt-1 text-[11px] text-emerald-300/80">Note: {order.resolution}</p>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel title="Agent audit trail" subtitle="Every decision is logged with its reason">
          {agent_log.length === 0 ? (
            <p className="px-5 py-8 text-center text-sm text-zinc-500">No agent activity yet.</p>
          ) : (
            <ol className="divide-y divide-white/5">
              {agent_log.map((entry, index) => (
                <li key={`${entry.created_at}-${index}`} className="flex gap-3 px-5 py-3">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-400" />
                  <div>
                    <p className="text-xs text-zinc-300">
                      <span className="font-medium text-zinc-100">{entry.action.replaceAll("_", " ")}</span>{" "}
                      <span className="text-zinc-500">· {entry.severity}</span>
                    </p>
                    <p className="mt-0.5 text-[11px] leading-relaxed text-zinc-500">{entry.reason}</p>
                    <p className="mt-0.5 text-[10px] text-zinc-600">{fmtDateTime(entry.created_at)}</p>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </Panel>
      </div>
    </div>
  );
}
