import { useEffect, useState } from "react";
import { api } from "../api";
import { useApi } from "../hooks/useApi";
import type { ModelMetrics, RetrainStatus } from "../types";
import { Panel, StatCard } from "../components/Panel";
import { ErrorBlock, LoadingBlock } from "../components/StateViews";
import { RefreshIcon } from "../components/icons";
import { fmtDateTime, fmtNumber, fmtPct } from "../lib/format";

function metricRow(
  label: string,
  key: keyof ModelMetrics,
  digits: number,
  baseline?: ModelMetrics,
  candidate?: ModelMetrics,
) {
  const format = (value?: number) => (value == null ? "—" : value.toFixed(digits));
  return (
    <tr key={label} className="border-b border-white/5 last:border-0">
      <td className="px-4 py-2.5 text-zinc-400">{label}</td>
      <td className="px-4 py-2.5 tabular-nums text-zinc-300">{format(baseline?.[key])}</td>
      <td className="px-4 py-2.5 tabular-nums font-medium text-zinc-100">
        {format(candidate?.[key])}
      </td>
    </tr>
  );
}

export function Models() {
  const models = useApi(api.models, []);
  const monitoring = useApi(api.monitoring, []);
  const [job, setJob] = useState<RetrainStatus | null>(null);
  const [starting, setStarting] = useState(false);
  const [retrainError, setRetrainError] = useState<string | null>(null);

  useEffect(() => {
    if (!job || (job.status !== "QUEUED" && job.status !== "RUNNING")) return;
    const timer = setInterval(async () => {
      try {
        const next = await api.retrainStatus(job.job_id);
        setJob(next);
        if (next.status === "DONE") {
          models.reload();
          monitoring.reload();
        }
      } catch (err) {
        setRetrainError(err instanceof Error ? err.message : "Polling failed");
      }
    }, 1500);
    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [job?.job_id, job?.status]);

  async function startRetrain() {
    setStarting(true);
    setRetrainError(null);
    try {
      setJob(await api.retrain());
    } catch (err) {
      setRetrainError(err instanceof Error ? err.message : "Could not start retraining");
    } finally {
      setStarting(false);
    }
  }

  if (models.loading && !models.data) {
    return (
      <Panel title="Models & monitoring">
        <LoadingBlock rows={5} />
      </Panel>
    );
  }

  if (models.error) {
    return (
      <Panel title="Models & monitoring">
        <ErrorBlock message={models.error} onRetry={models.reload} />
      </Panel>
    );
  }

  if (!models.data) return null;

  const production = models.data.production;
  const latestRun = models.data.runs[0];
  const testMetrics = latestRun?.metrics.test;
  const validation = production?.metrics;

  const retrainRunning = job?.status === "QUEUED" || job?.status === "RUNNING";

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-xl font-semibold tracking-tight text-zinc-100 sm:text-2xl">
          Models & monitoring
        </h1>
        <p className="mt-1 max-w-3xl text-sm text-zinc-400">
          Two regressors compete on identical features; the lowest validation RMSE is promoted to
          production. Metrics are mirrored into SQLite so redeploys cannot erase the history.
        </p>
      </header>

      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <StatCard
          label="Production model"
          value={production?.production_model ?? "—"}
          hint={production ? `selected by ${production.selection_metric}` : "no production pointer"}
          tone="accent"
        />
        <StatCard
          label="Test RMSE"
          value={testMetrics ? `${fmtNumber(testMetrics.rmse, 1)}c` : "—"}
          hint="official C-MAPSS test split"
          tone="warning"
        />
        <StatCard
          label="Test MAE"
          value={testMetrics ? `${fmtNumber(testMetrics.mae, 1)}c` : "—"}
          hint="mean absolute error"
        />
        <StatCard
          label="Critical recall"
          value={testMetrics ? fmtPct(testMetrics.critical_recall, 0) : "—"}
          hint="of engines truly at ≤15 cycles"
          tone="success"
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-5">
        <Panel
          className="xl:col-span-3"
          title="Baseline vs candidate"
          subtitle="Held-out validation engines — no engine appears in both splits"
        >
          <div className="overflow-x-auto">
            <table className="w-full min-w-[460px] text-left text-sm">
              <thead className="text-[11px] uppercase tracking-[0.12em] text-zinc-500">
                <tr className="border-b border-white/5">
                  <th className="px-4 py-2.5 font-medium">Metric</th>
                  <th className="px-4 py-2.5 font-medium">Ridge baseline</th>
                  <th className="px-4 py-2.5 font-medium">Gradient boosting</th>
                </tr>
              </thead>
              <tbody>
                {metricRow("RMSE (cycles)", "rmse", 2, validation?.baseline, validation?.candidate)}
                {metricRow("MAE (cycles)", "mae", 2, validation?.baseline, validation?.candidate)}
                {metricRow("PHM score", "phm_score", 0, validation?.baseline, validation?.candidate)}
              </tbody>
            </table>
          </div>
          <div className="border-t border-white/5 px-4 py-3 text-[11px] leading-relaxed text-zinc-600">
            PHM is the NASA scoring function: a late prediction (claiming life that is not there)
            is punished far harder than an early one. Lower is better for RMSE, MAE and PHM;
            critical recall is reported on the test split.
          </div>
        </Panel>

        <Panel
          className="xl:col-span-2"
          title="Closed loop"
          subtitle="Retrain promotes a new version and re-scores the fleet"
        >
          <div className="space-y-4 p-5">
            <p className="text-xs leading-relaxed text-zinc-400">
              This button runs the real Layer-2 pipeline (features → fit → validate → promote →
              triage → work orders). Nothing is simulated; expect 30–60 seconds on a free host.
            </p>
            <button
              type="button"
              onClick={startRetrain}
              disabled={starting || retrainRunning}
              className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-amber-400/30 bg-amber-400/10 px-4 py-2.5 text-sm font-medium text-amber-200 transition hover:bg-amber-400/20 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <RefreshIcon className={`h-4 w-4 ${retrainRunning ? "animate-spin" : ""}`} />
              {retrainRunning ? "Retraining…" : "Retrain & re-score fleet"}
            </button>

            {retrainError ? (
              <p className="rounded-lg border border-red-500/25 bg-red-500/5 px-3 py-2 text-[11px] text-red-300">
                {retrainError}
              </p>
            ) : null}

            {job ? (
              <div className="rounded-lg border border-white/5 bg-[#0b0b0e] p-3">
                <div className="flex items-center justify-between gap-2">
                  <span
                    className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
                      job.status === "DONE"
                        ? "bg-emerald-500/10 text-emerald-300"
                        : job.status === "ERROR"
                          ? "bg-red-500/10 text-red-300"
                          : "bg-amber-400/10 text-amber-200"
                    }`}
                  >
                    {job.status}
                  </span>
                  <span className="font-mono text-[10px] text-zinc-600">{job.job_id}</span>
                </div>
                <p className="mt-2 text-[11px] leading-relaxed text-zinc-400">
                  {job.message ??
                    "Queued. The worker will fit both models, promote the winner and rebuild the work-order queue."}
                </p>
              </div>
            ) : null}

            <p className="text-[10px] leading-relaxed text-zinc-600">
              Requires the raw NASA files on the server. On the free tier the disk is ephemeral:
              orders you resolve reset on the next deploy.
            </p>
          </div>
        </Panel>
      </div>

      <Panel
        title="Run history"
        subtitle="Mirrored from MLflow into SQLite — survives redeploys"
      >
        <div className="overflow-x-auto">
          <table className="w-full min-w-[700px] text-left text-sm">
            <thead className="text-[11px] uppercase tracking-[0.12em] text-zinc-500">
              <tr className="border-b border-white/5">
                <th className="px-5 py-2.5 font-medium">Run</th>
                <th className="px-3 py-2.5 font-medium">Model</th>
                <th className="px-3 py-2.5 font-medium">Trained</th>
                <th className="px-3 py-2.5 font-medium">Test RMSE</th>
                <th className="px-5 py-2.5 text-right font-medium">State</th>
              </tr>
            </thead>
            <tbody>
              {models.data.runs.map((run) => (
                <tr key={run.run_id} className="border-b border-white/5 last:border-0">
                  <td className="px-5 py-2.5 font-mono text-[11px] text-zinc-400">
                    {run.run_id.slice(0, 28)}
                  </td>
                  <td className="px-3 py-2.5 text-zinc-300">{run.production_model}</td>
                  <td className="px-3 py-2.5 text-xs text-zinc-400">
                    {fmtDateTime(run.trained_at)}
                  </td>
                  <td className="px-3 py-2.5 tabular-nums text-zinc-300">
                    {run.metrics.test ? `${fmtNumber(run.metrics.test.rmse, 1)}c` : "—"}
                  </td>
                  <td className="px-5 py-2.5 text-right">
                    {run.is_production ? (
                      <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-300">
                        production
                      </span>
                    ) : (
                      <span className="text-[10px] uppercase tracking-wide text-zinc-600">
                        archived
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <div className="grid gap-6 xl:grid-cols-2">
        <Panel title="Predicted RUL distribution" subtitle="Current fleet snapshot">
          {monitoring.data ? (
            <div className="space-y-3 p-5">
              {Object.entries(monitoring.data.rul_bands).map(([band, count]) => (
                <div key={band} className="flex items-center gap-3">
                  <span className="w-14 text-right font-mono text-[11px] text-zinc-500">{band}</span>
                  <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-white/5">
                    <div
                      className={`h-full rounded-full ${
                        band === "0-15"
                          ? "bg-red-500"
                          : band === "16-30"
                            ? "bg-orange-500"
                            : band === "31-60"
                              ? "bg-amber-400"
                              : "bg-emerald-500"
                      }`}
                      style={{ width: `${(count / 100) * 100}%` }}
                    />
                  </div>
                  <span className="w-8 tabular-nums text-xs text-zinc-300">{count}</span>
                </div>
              ))}
              <p className="pt-1 text-[11px] text-zinc-600">Cycles of remaining life · 100 machines</p>
            </div>
          ) : (
            <LoadingBlock rows={5} />
          )}
        </Panel>

        <Panel title="Recent agent decisions" subtitle="Newest first">
          {monitoring.data ? (
            <ul className="max-h-[320px] divide-y divide-white/5 overflow-y-auto">
              {monitoring.data.activity.slice(0, 8).map((entry, index) => (
                <li key={`${entry.created_at}-${index}`} className="px-5 py-3">
                  <p className="text-xs text-zinc-300">
                    <span className="font-medium text-zinc-100">
                      Engine #{entry.engine_id} · {entry.severity}
                    </span>{" "}
                    <span className="text-zinc-500">{entry.action.replaceAll("_", " ")}</span>
                  </p>
                  <p className="mt-0.5 text-[11px] text-zinc-500">{entry.reason}</p>
                </li>
              ))}
            </ul>
          ) : (
            <LoadingBlock rows={5} />
          )}
        </Panel>
      </div>
    </div>
  );
}
