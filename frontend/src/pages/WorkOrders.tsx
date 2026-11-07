import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useApi } from "../hooks/useApi";
import { useOwnerKey } from "../hooks/useOwnerKey";
import type { OrderStatus } from "../types";
import { Panel } from "../components/Panel";
import { SeverityBadge } from "../components/SeverityBadge";
import { EmptyBlock, ErrorBlock, LoadingBlock } from "../components/StateViews";
import { fmtDateTime, fmtNumber, fmtPct } from "../lib/format";

type Tab = "ACTIVE" | "OPEN" | "HUMAN_REVIEW" | "HISTORY";

const tabs: Array<{ id: Tab; label: string; hint: string }> = [
  { id: "ACTIVE", label: "Active queue", hint: "Everything still in play" },
  { id: "OPEN", label: "Auto-created", hint: "CRITICAL / HIGH — no human needed" },
  { id: "HUMAN_REVIEW", label: "Human review", hint: "MEDIUM — a person decides" },
  { id: "HISTORY", label: "Settled", hint: "Resolved or dismissed" },
];

function fetcherFor(tab: Tab) {
  if (tab === "ACTIVE") return api.workOrders({ activeOnly: true });
  if (tab === "OPEN") return api.workOrders({ status: "OPEN" });
  if (tab === "HUMAN_REVIEW") return api.workOrders({ status: "HUMAN_REVIEW" });
  return api.workOrders();
}

export function WorkOrders() {
  const [tab, setTab] = useState<Tab>("ACTIVE");
  const { data, error, loading, reload } = useApi(() => fetcherFor(tab), [tab]);
  const { unlocked } = useOwnerKey();
  const [busy, setBusy] = useState<number | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const orders =
    tab === "HISTORY"
      ? (data ?? []).filter((order) => order.status === "RESOLVED" || order.status === "DISMISSED")
      : (data ?? []);

  async function handleResolve(id: number, status: "RESOLVED" | "DISMISSED") {
    setBusy(id);
    setActionError(null);
    setNotice(null);
    try {
      const note =
        status === "RESOLVED"
          ? "Resolved from the dashboard"
          : "Dismissed from the dashboard as a false alarm";
      await api.resolve(id, status, note);
      setNotice(`Order #${id} marked ${status.toLowerCase()}.`);
      reload();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-xl font-semibold tracking-tight text-zinc-100 sm:text-2xl">
          Work orders
        </h1>
        <p className="mt-1 max-w-3xl text-sm text-zinc-400">
          The agent opens CRITICAL and HIGH orders automatically. MEDIUM goes to a human queue —
          that is the only place a person is asked to step in.
        </p>
      </header>

      <div className="flex flex-wrap gap-1.5">
        {tabs.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setTab(item.id)}
            title={item.hint}
            className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition ${
              tab === item.id
                ? "border-amber-400/30 bg-amber-400/10 text-amber-200"
                : "border-white/10 text-zinc-400 hover:border-white/20 hover:text-zinc-200"
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>

      {notice ? (
        <p className="rounded-lg border border-emerald-500/25 bg-emerald-500/5 px-4 py-2.5 text-xs text-emerald-300">
          {notice}
        </p>
      ) : null}
      {actionError ? (
        <p className="rounded-lg border border-red-500/25 bg-red-500/5 px-4 py-2.5 text-xs text-red-300">
          {actionError}
          {actionError.toLowerCase().includes("token") || actionError.toLowerCase().includes("owner")
            ? " — unlock Owner access in the top bar with the server's SHM_API_TOKEN."
            : ""}
        </p>
      ) : null}

      <Panel
        title={tabs.find((item) => item.id === tab)?.label}
        subtitle={`${orders.length} order${orders.length === 1 ? "" : "s"} · ${tabs.find((item) => item.id === tab)?.hint}`}
      >
        {loading && !data ? (
          <LoadingBlock rows={5} />
        ) : error ? (
          <ErrorBlock message={error} onRetry={reload} />
        ) : orders.length === 0 ? (
          <EmptyBlock
            title="Nothing in this queue"
            hint={
              tab === "HUMAN_REVIEW"
                ? "No MEDIUM machine needs a human decision right now — that is a good day."
                : "Try another tab, or run the fleet sync to generate fresh orders."
            }
          />
        ) : (
          <>
            {!unlocked ? (
              <p className="border-b border-white/5 bg-white/[0.02] px-4 py-2.5 text-[11px] text-zinc-500">
                Read-only view · unlock <span className="text-zinc-300">Owner access</span> in the
                top bar to resolve or dismiss orders.
              </p>
            ) : null}
            <ul className="divide-y divide-white/5">
              {orders.map((order) => {
              const isActive = order.status === "OPEN" || order.status === "HUMAN_REVIEW";
              return (
                <li key={order.id} className="px-4 py-4 sm:px-5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <SeverityBadge severity={order.severity} />
                        <Link
                          to={`/engines/${order.engine_id}`}
                          className="text-sm font-medium text-zinc-100 hover:text-amber-300"
                        >
                          Engine #{order.engine_id}
                        </Link>
                        <span className="text-[11px] text-zinc-600">order #{order.id}</span>
                      </div>
                      <p className="mt-2 max-w-3xl text-xs leading-relaxed text-zinc-400">
                        {order.reason}
                      </p>
                      <p className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-zinc-600">
                        <span>RUL {fmtNumber(order.predicted_rul)}c</span>
                        <span>anomaly {fmtPct(order.anomaly, 1)}</span>
                        <span>trend {order.rul_slope.toFixed(2)}c/cy</span>
                        <span>opened {fmtDateTime(order.created_at)}</span>
                      </p>
                      {order.resolution ? (
                        <p className="mt-1 text-[11px] text-zinc-500">
                          Resolution: {order.resolution}
                        </p>
                      ) : null}
                    </div>

                    <div className="flex shrink-0 items-center gap-2">
                      {isActive ? (
                        <>
                          <button
                            type="button"
                            disabled={busy === order.id || !unlocked}
                            title={unlocked ? "Mark this order resolved" : "Unlock Owner access first"}
                            onClick={() => handleResolve(order.id, "RESOLVED")}
                            className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-1.5 text-xs font-medium text-emerald-300 transition hover:bg-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            Resolve
                          </button>
                          <button
                            type="button"
                            disabled={busy === order.id || !unlocked}
                            title={unlocked ? "Dismiss as a false alarm" : "Unlock Owner access first"}
                            onClick={() => handleResolve(order.id, "DISMISSED")}
                            className="rounded-lg border border-white/10 px-3 py-1.5 text-xs font-medium text-zinc-400 transition hover:border-white/20 hover:text-zinc-200 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            Dismiss
                          </button>
                        </>
                      ) : (
                        <span className="rounded-full border border-white/10 px-2.5 py-1 text-[10px] font-medium uppercase tracking-wide text-zinc-500">
                          {order.status as OrderStatus}
                        </span>
                      )}
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
          </>
        )}
      </Panel>
    </div>
  );
}
