import { FormEvent, useState } from "react";
import { api } from "../api";
import { useOwnerKey } from "../hooks/useOwnerKey";

/**
 * Owner-only write access.
 *
 * Visitors always get the full read-only dashboard. Unlocking only stores the
 * key in this browser — it is never shipped in the bundle.
 */
export function OwnerAccess() {
  const { unlocked, update } = useOwnerKey();
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ownerConfigured, setOwnerConfigured] = useState<boolean | null>(null);

  async function openPanel() {
    setOpen(true);
    setError(null);
    try {
      const health = await api.health();
      setOwnerConfigured(health.owner_configured ?? true);
    } catch {
      setOwnerConfigured(null);
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    const candidate = value.trim();
    if (!candidate) return;
    setBusy(true);
    setError(null);
    update(candidate);
    try {
      await api.verifyOwner();
      setOpen(false);
      setValue("");
    } catch (err) {
      update("");
      setError(err instanceof Error ? err.message : "Could not verify the key");
    } finally {
      setBusy(false);
    }
  }

  function lock() {
    update("");
    setOpen(false);
    setValue("");
    setError(null);
  }

  return (
    <>
      <button
        type="button"
        onClick={() => (open || unlocked ? setOpen((v) => !v) : openPanel())}
        title={
          unlocked
            ? "Owner access is unlocked in this browser"
            : "Visitors can view everything; only the owner can change data"
        }
        className={`flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs font-medium transition ${
          unlocked
            ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/20"
            : "border-white/10 text-zinc-400 hover:border-white/20 hover:text-zinc-100"
        }`}
      >
        <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={1.8}>
          <rect x="4" y="10" width="16" height="11" rx="2.5" />
          <path d="M8 10V7a4 4 0 0 1 8 0v3" strokeLinecap="round" />
        </svg>
        <span className="hidden sm:inline">{unlocked ? "Owner on" : "Owner access"}</span>
      </button>

      {open ? (
        <div
          className="fixed inset-0 z-50 grid place-items-center bg-black/70 p-4 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          aria-labelledby="owner-access-title"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setOpen(false);
          }}
        >
          <div className="w-full max-w-md rounded-2xl border border-white/10 bg-[#0e0e12] p-5 shadow-2xl">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 id="owner-access-title" className="text-sm font-semibold text-zinc-100">
                  Owner access
                </h2>
                <p className="mt-1 text-xs leading-relaxed text-zinc-400">
                  Everyone can explore this dashboard. Resolving work orders and retraining are
                  owner-only.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setOpen(false)}
                aria-label="Close"
                className="rounded-md p-1 text-zinc-500 transition hover:bg-white/5 hover:text-zinc-200"
              >
                <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2}>
                  <path d="M6 6l12 12M18 6L6 18" strokeLinecap="round" />
                </svg>
              </button>
            </div>

            {unlocked ? (
              <div className="mt-5 space-y-4">
                <p className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 px-3 py-2.5 text-xs text-emerald-300">
                  Unlocked in this browser. Write actions are enabled.
                </p>
                <button
                  type="button"
                  onClick={lock}
                  className="w-full rounded-lg border border-white/10 px-4 py-2.5 text-sm font-medium text-zinc-300 transition hover:border-white/20 hover:text-zinc-100"
                >
                  Lock this browser
                </button>
              </div>
            ) : (
              <form onSubmit={submit} className="mt-5 space-y-3">
                {ownerConfigured === false ? (
                  <p className="rounded-lg border border-amber-400/25 bg-amber-400/5 px-3 py-2.5 text-xs leading-relaxed text-amber-200">
                    This server has no owner key configured, so writes are disabled. Set
                    <code className="mx-1 rounded bg-black/30 px-1 py-0.5 font-mono text-[10px]">
                      SHM_API_TOKEN
                    </code>
                    on the backend, then enter the same value here.
                  </p>
                ) : null}

                <label className="block">
                  <span className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">
                    Owner key
                  </span>
                  <input
                    type="password"
                    value={value}
                    onChange={(event) => setValue(event.target.value)}
                    autoFocus
                    autoComplete="off"
                    placeholder="Paste the key from the server"
                    className="mt-1.5 w-full rounded-lg border border-white/10 bg-[#08080a] px-3 py-2 text-sm text-zinc-100 outline-none transition placeholder:text-zinc-600 focus:border-amber-400/40"
                  />
                </label>

                {error ? (
                  <p className="rounded-lg border border-red-500/25 bg-red-500/5 px-3 py-2 text-xs text-red-300">
                    {error}
                  </p>
                ) : null}

                <div className="flex gap-2 pt-1">
                  <button
                    type="submit"
                    disabled={busy || !value.trim()}
                    className="flex-1 rounded-lg border border-amber-400/30 bg-amber-400/10 px-4 py-2.5 text-sm font-medium text-amber-200 transition hover:bg-amber-400/20 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {busy ? "Verifying…" : "Unlock"}
                  </button>
                  <button
                    type="button"
                    onClick={() => setOpen(false)}
                    className="rounded-lg border border-white/10 px-4 py-2.5 text-sm font-medium text-zinc-400 transition hover:border-white/20 hover:text-zinc-200"
                  >
                    Cancel
                  </button>
                </div>

                <p className="pt-1 text-[10px] leading-relaxed text-zinc-600">
                  The key is checked by the server and stored only in this browser — never in the
                  public site bundle.
                </p>
              </form>
            )}
          </div>
        </div>
      ) : null}
    </>
  );
}
