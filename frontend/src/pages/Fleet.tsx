import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useApi } from "../hooks/useApi";
import type { Severity } from "../types";
import { SeverityBadge } from "../components/SeverityBadge";
import { Panel, StatCard } from "../components/Panel";
import { EmptyBlock, ErrorBlock, LoadingBlock } from "../components/StateViews";
import { SearchIcon } from "../components/icons";
import {
  SEVERITY_ORDER,
  fmtDateTime,
  fmtNumber,
  fmtPct,
  rulTone,
  severityDot,
  timeAgo,
} from "../lib/format";

const severities: Array<Severity | "ALL"> = ["ALL", ...SEVERITY_ORDER];

export function Fleet() {
  const { data, error, loading, reload } = useApi(api.fleet, []);
  const [query, setQuery] = useState("");
  const [severity, setSeverity] = useState<Severity | "ALL">("ALL");

  const engines = useMemo(() => {
    if (!data) return [];
    return data.engines.filter((engine) => {
      const matchesSeverity = severity === "ALL" || engine.severity === severity;
      const matchesQuery = query.trim() === "" || String(engine.engine_id).includes(query.trim());
      return matchesSeverity && matchesQuery;
    });
  }, [data, query, severity]);

  if (loading && !data) {
    return (
      <Panel title="Fleet overview">
        <LoadingBlock rows={6} />
      </Panel>
    );
  }

  if (error) {
    return (
      <Panel title="Fleet overview">
        <ErrorBlock message={error} onRetry={reload} />
      </Panel>
    );
  }

  if (!data) return null;

  const total = data.total_engines;
  const lastSync = data.engines[0]?.updated_at;

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-zinc-100 sm:text-2xl">
            Fleet overview
          </h1>
          <p className="mt-1 max-w-2xl text-sm text-zinc-400">
            Remaining useful life for every machine in the {data.subset} fleet, ranked by the
            triage agent. Red machines already have a work order.
          </p>
        </div>
        <p className="text-xs text-zinc-500">
          Last scored {timeAgo(lastSync)} · {fmtDateTime(lastSync)}
        </p>
      </header>

      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <StatCard
          label="Machines monitored"
          value={fmtNumber(total)}
          hint={`${data.subset} test fleet`}
        />
        <StatCard
          label="Critical"
          value={fmtNumber(data.severity.CRITICAL ?? 0)}
          hint={`${fmtPct(data.kpis.critical_share)} of the fleet`}
          tone="danger"
        />
        <StatCard
          label="Avg. predicted RUL"
          value={`${fmtNumber(data.kpis.avg_predicted_rul)}c`}
          hint={`median ${fmtNumber(data.kpis.median_predicted_rul)} cycles`}
          tone="warning"
        />
        <StatCard
          label="Open work orders"
          value={fmtNumber(data.kpis.open_orders)}
          hint={`${data.work_orders.HUMAN_REVIEW ?? 0} waiting for a human`}
          tone="success"
        />
      </div>

      <Panel
        title="Severity distribution"
        subtitle="One machine, one severity band — decided by rules, explained in the reason field."
      >
        <div className="px-5 pb-5 pt-4">
          <div className="flex h-3 w-full overflow-hidden rounded-full bg-white/5">
            {SEVERITY_ORDER.map((key) => {
              const count = data.severity[key] ?? 0;
              if (!count) return null;
              return (
                <div
                  key={key}
                  className={`${severityDot[key]} h-full`}
                  style={{ width: `${(count / total) * 100}%` }}
                  title={`${key}: ${count}`}
                />
              );
            })}
          </div>
          <div className="mt-3 flex flex-wrap gap-x-6 gap-y-2">
            {SEVERITY_ORDER.map((key) => (
              <span key={key} className="flex items-center gap-2 text-xs text-zinc-400">
                <span className={`h-2 w-2 rounded-full ${severityDot[key]}`} />
                {key}
                <span className="font-medium tabular-nums text-zinc-200">
                  {data.severity[key] ?? 0}
                </span>
              </span>
            ))}
          </div>
        </div>
      </Panel>

      <Panel
        title="Machines"
        subtitle={`${engines.length} of ${total} shown`}
        action={
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative">
              <SearchIcon className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-zinc-500" />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                inputMode="numeric"
                placeholder="Engine id"
                aria-label="Filter by engine id"
                className="w-28 rounded-lg border border-white/10 bg-[#0b0b0e] py-1.5 pl-8 pr-2 text-xs text-zinc-200 outline-none placeholder:text-zinc-600 focus:border-amber-400/40"
              />
            </div>
            <select
              value={severity}
              onChange={(event) => setSeverity(event.target.value as Severity | "ALL")}
              aria-label="Filter by severity"
              className="rounded-lg border border-white/10 bg-[#0b0b0e] px-2 py-1.5 text-xs text-zinc-300 outline-none focus:border-amber-400/40"
            >
              {severities.map((value) => (
                <option key={value} value={value}>
                  {value === "ALL" ? "All severities" : value}
                </option>
              ))}
            </select>
          </div>
        }
      >
        {engines.length === 0 ? (
          <EmptyBlock
            title="No machines match this filter"
            hint="Clear the engine id or pick a different severity band."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[820px] text-left text-sm">
              <thead className="text-[11px] uppercase tracking-[0.12em] text-zinc-500">
                <tr className="border-b border-white/5">
                  <th className="px-5 py-2.5 font-medium">Engine</th>
                  <th className="px-3 py-2.5 font-medium">Severity</th>
                  <th className="px-3 py-2.5 font-medium">Predicted RUL</th>
                  <th className="px-3 py-2.5 font-medium">Anomaly</th>
                  <th className="px-3 py-2.5 font-medium">Trend</th>
                  <th className="px-3 py-2.5 font-medium">True RUL*</th>
                  <th className="px-5 py-2.5 text-right font-medium">Cycle</th>
                </tr>
              </thead>
              <tbody>
                {engines.map((engine) => (
                  <tr
                    key={engine.engine_id}
                    className="group border-b border-white/5 last:border-0 hover:bg-white/[0.02]"
                  >
                    <td className="px-5 py-2.5">
                      <Link
                        to={`/engines/${engine.engine_id}`}
                        className="font-medium text-zinc-200 group-hover:text-amber-300"
                      >
                        Engine #{engine.engine_id}
                      </Link>
                    </td>
                    <td className="px-3 py-2.5">
                      <SeverityBadge severity={engine.severity} />
                    </td>
                    <td className="px-3 py-2.5">
                      <div className="flex items-center gap-2">
                        <span className="w-11 text-right font-medium tabular-nums text-zinc-100">
                          {fmtNumber(engine.predicted_rul)}c
                        </span>
                        <span className="h-1.5 w-24 overflow-hidden rounded-full bg-white/5">
                          <span
                            className={`block h-full ${rulTone(engine.predicted_rul)}`}
                            style={{
                              width: `${Math.max(4, Math.min(100, (engine.predicted_rul / 160) * 100))}%`,
                            }}
                          />
                        </span>
                      </div>
                    </td>
                    <td className="px-3 py-2.5 tabular-nums text-zinc-300">
                      {fmtPct(engine.anomaly, 1)}
                    </td>
                    <td
                      className={`px-3 py-2.5 tabular-nums ${
                        engine.rul_slope < -1.5 ? "text-orange-300" : "text-zinc-400"
                      }`}
                    >
                      {engine.rul_slope.toFixed(2)}c/cy
                    </td>
                    <td className="px-3 py-2.5 tabular-nums text-zinc-500">
                      {engine.true_rul ?? "—"}
                    </td>
                    <td className="px-5 py-2.5 text-right tabular-nums text-zinc-400">
                      {engine.cycle}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="border-t border-white/5 px-5 py-3 text-[11px] text-zinc-600">
          * True RUL is the official NASA label, shown for offline evaluation only. In a real
          fleet it is unknown until the machine actually fails.
        </p>
      </Panel>
    </div>
  );
}
