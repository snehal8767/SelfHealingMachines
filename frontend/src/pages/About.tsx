import { api, API_URL } from "../api";
import { useApi } from "../hooks/useApi";
import { Panel } from "../components/Panel";
import { ErrorBlock, LoadingBlock } from "../components/StateViews";
import { fmtDateTime, fmtNumber, fmtPct } from "../lib/format";

const stack = [
  "Python 3.12",
  "pandas · numpy",
  "scikit-learn",
  "MLflow",
  "FastAPI",
  "SQLite",
  "React + Vite",
  "Tailwind CSS",
];

export function About() {
  const { data, error, loading, reload } = useApi(api.about, []);

  if (loading && !data) {
    return (
      <Panel title="About this prototype">
        <LoadingBlock rows={5} />
      </Panel>
    );
  }

  if (error) {
    return (
      <Panel title="About this prototype">
        <ErrorBlock message={error} onRetry={reload} />
      </Panel>
    );
  }

  if (!data) return null;

  const testMetrics = data.models.metrics?.candidate;

  return (
    <div className="space-y-6">
      <header className="max-w-3xl">
        <span className="inline-flex rounded-full border border-amber-400/25 bg-amber-400/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-amber-200">
          TELIPORT · Case Study 1
        </span>
        <h1 className="mt-3 text-xl font-semibold tracking-tight text-zinc-100 sm:text-2xl">
          {data.project}
        </h1>
        <p className="mt-2 text-sm leading-relaxed text-zinc-400">
          A closed loop, not a notebook: sensor history becomes an early degradation signal, the
          signal becomes a Remaining Useful Life estimate, and a deterministic agent turns that
          estimate into a maintenance work order. People only see the exceptions.
        </p>
      </header>

      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-xl border border-white/5 bg-[#111114] p-4">
          <p className="text-[11px] uppercase tracking-[0.14em] text-zinc-500">Dataset</p>
          <p className="mt-2 text-sm font-medium text-zinc-100">NASA C-MAPSS</p>
          <p className="mt-1 text-xs text-zinc-500">
            {String(data.dataset.subset)} · {String(data.dataset.sensors)} sensors +{" "}
            {String(data.dataset.settings)} settings
          </p>
        </div>
        <div className="rounded-xl border border-white/5 bg-[#111114] p-4">
          <p className="text-[11px] uppercase tracking-[0.14em] text-zinc-500">Production model</p>
          <p className="mt-2 text-sm font-medium text-zinc-100">
            {data.models.production_model ?? "—"}
          </p>
          <p className="mt-1 text-xs text-zinc-500">
            trained {fmtDateTime(data.models.trained_at)}
          </p>
        </div>
        <div className="rounded-xl border border-white/5 bg-[#111114] p-4">
          <p className="text-[11px] uppercase tracking-[0.14em] text-zinc-500">Test RMSE / recall</p>
          <p className="mt-2 text-sm font-medium text-zinc-100">
            {testMetrics ? `${fmtNumber(testMetrics.rmse, 1)}c` : "—"}{" "}
            <span className="text-zinc-500">/</span>{" "}
            {testMetrics ? fmtPct(testMetrics.critical_recall, 0) : "—"}
          </p>
          <p className="mt-1 text-xs text-zinc-500">official C-MAPSS test split</p>
        </div>
      </div>

      <Panel title="Architecture" subtitle="Every arrow is implemented and covered by tests">
        <ol className="grid gap-2 p-5 sm:grid-cols-2">
          {data.architecture.map((step, index) => (
            <li
              key={step}
              className="flex gap-3 rounded-lg border border-white/5 bg-[#0b0b0e] px-3.5 py-3"
            >
              <span className="grid h-6 w-6 shrink-0 place-items-center rounded-md bg-amber-400/10 text-[11px] font-semibold text-amber-300">
                {index + 1}
              </span>
              <span className="text-xs leading-relaxed text-zinc-300">{step}</span>
            </li>
          ))}
        </ol>
        <div className="border-t border-white/5 px-5 py-3 text-[11px] leading-relaxed text-zinc-600">
          The triage agent is plain thresholds — RUL, anomaly percentile and RUL slope — with a
          human-readable reason attached to every decision. No LLM is called anywhere in the
          runtime path.
        </div>
      </Panel>

      <div className="grid gap-6 xl:grid-cols-2">
        <Panel title="Dataset provenance" subtitle="Public benchmark, reproducible download">
          <dl className="divide-y divide-white/5">
            {Object.entries(data.dataset).map(([key, value]) => (
              <div key={key} className="flex items-start justify-between gap-4 px-5 py-2.5">
                <dt className="text-xs capitalize text-zinc-500">{key.replaceAll("_", " ")}</dt>
                <dd className="max-w-[60%] text-right text-xs text-zinc-300">{String(value)}</dd>
              </div>
            ))}
          </dl>
          <p className="border-t border-white/5 px-5 py-3 text-[11px] leading-relaxed text-zinc-600">
            Simulated run-to-failure trajectories with true RUL labels. Predictions here are
            benchmark results, not operational advice for a real asset.
          </p>
        </Panel>

        <Panel title="Known limitations" subtitle="Stated up front, not hidden in a footnote">
          <ul className="space-y-2.5 p-5">
            {data.limitations.map((limitation) => (
              <li key={limitation} className="flex gap-2 text-xs leading-relaxed text-zinc-400">
                <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-amber-400" />
                {limitation}
              </li>
            ))}
          </ul>
        </Panel>
      </div>

      <Panel title="Built with" subtitle="Open-source only">
        <div className="flex flex-wrap gap-2 p-5">
          {stack.map((item) => (
            <span
              key={item}
              className="rounded-full border border-white/10 bg-white/[0.03] px-3 py-1 text-[11px] text-zinc-300"
            >
              {item}
            </span>
          ))}
          <a
            href={`${API_URL}/docs`}
            target="_blank"
            rel="noreferrer"
            className="rounded-full border border-amber-400/25 bg-amber-400/10 px-3 py-1 text-[11px] font-medium text-amber-200 hover:bg-amber-400/20"
          >
            Interactive API docs ↗
          </a>
        </div>
      </Panel>
    </div>
  );
}
