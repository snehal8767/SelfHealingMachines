import { NavLink, Outlet } from "react-router-dom";
import { api, API_URL } from "../api";
import { useApi } from "../hooks/useApi";
import { OwnerAccess } from "./OwnerAccess";
import { ChipIcon, GaugeIcon, InfoIcon, PulseIcon, WrenchIcon } from "./icons";

const nav = [
  { to: "/", label: "Fleet", icon: GaugeIcon, end: true },
  { to: "/work-orders", label: "Work orders", icon: WrenchIcon, end: false },
  { to: "/models", label: "Models & monitoring", icon: ChipIcon, end: false },
  { to: "/about", label: "About", icon: InfoIcon, end: false },
];

function navClass({ isActive }: { isActive: boolean }) {
  return [
    "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition",
    isActive
      ? "bg-amber-400/10 text-amber-200"
      : "text-zinc-400 hover:bg-white/5 hover:text-zinc-100",
  ].join(" ");
}

function Brand() {
  return (
    <div className="flex items-center gap-3">
      <div className="grid h-9 w-9 place-items-center rounded-lg border border-amber-400/25 bg-amber-400/10">
        <PulseIcon className="h-5 w-5 text-amber-300" />
      </div>
      <div className="leading-tight">
        <p className="text-sm font-semibold tracking-tight text-zinc-100">Self-Healing Machines</p>
        <p className="text-[11px] text-zinc-500">Fleet health · NASA C-MAPSS</p>
      </div>
    </div>
  );
}

export function Layout() {
  const health = useApi(api.health, []);
  const online = health.data?.status === "ok";

  return (
    <div className="min-h-screen">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r border-white/5 bg-[#0b0b0e] px-4 py-5 lg:flex">
        <Brand />
        <nav className="mt-8 space-y-1" aria-label="Primary">
          {nav.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} className={navClass}>
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="mt-auto space-y-3 pt-6">
          <div className="rounded-lg border border-white/5 bg-[#111114] p-3">
            <div className="flex items-center gap-2">
              <span
                className={`h-2 w-2 rounded-full ${
                  health.loading ? "bg-zinc-500" : online ? "bg-emerald-500" : "bg-red-500"
                }`}
              />
              <p className="text-xs font-medium text-zinc-300">
                {health.loading ? "Checking API…" : online ? "API online" : "API offline"}
              </p>
            </div>
            <p className="mt-1 truncate text-[10px] text-zinc-600" title={API_URL}>
              {online && health.data
                ? `${health.data.engines} engines · ${health.data.subset}`
                : API_URL}
            </p>
          </div>
          <p className="px-1 text-[10px] leading-relaxed text-zinc-600">
            Deterministic triage agent · no LLM
            <br />
            Round 2 prototype
          </p>
        </div>
      </aside>

      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 border-b border-white/5 bg-[#08080a]/85 backdrop-blur">
          <div className="flex items-center justify-between gap-4 px-4 py-3 lg:px-8">
            <div className="lg:hidden">
              <Brand />
            </div>
            <div className="hidden items-center gap-2 lg:flex">
              <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[11px] font-medium text-zinc-300">
                {health.data?.subset ?? "FD001"}
              </span>
              <span className="rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2.5 py-1 text-[11px] font-medium text-emerald-300">
                C-MAPSS · test split
              </span>
            </div>
            <div className="flex items-center gap-2">
              <a
                href={`${API_URL}/docs`}
                target="_blank"
                rel="noreferrer"
                className="hidden rounded-lg border border-white/10 px-3 py-1.5 text-xs font-medium text-zinc-400 transition hover:border-white/20 hover:text-zinc-100 sm:inline-block"
              >
                API docs ↗
              </a>
              <OwnerAccess />
            </div>
          </div>

          <nav className="flex gap-1 overflow-x-auto px-3 pb-2 lg:hidden" aria-label="Primary mobile">
            {nav.map(({ to, label, icon: Icon, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  `flex shrink-0 items-center gap-2 rounded-lg px-3 py-1.5 text-xs ${
                    isActive
                      ? "bg-amber-400/10 text-amber-200"
                      : "text-zinc-400 hover:bg-white/5"
                  }`
                }
              >
                <Icon className="h-3.5 w-3.5" />
                {label}
              </NavLink>
            ))}
          </nav>
        </header>

        <main className="mx-auto w-full max-w-[1440px] px-4 py-6 lg:px-8 lg:py-8">
          <Outlet />
        </main>

        <footer className="mx-auto w-full max-w-[1440px] px-4 pb-8 text-[11px] text-zinc-600 lg:px-8">
          Data: NASA C-MAPSS Turbofan Engine Degradation Simulation Data Set (public domain).
          Predictions are benchmark results, not operational advice.
        </footer>
      </div>
    </div>
  );
}
