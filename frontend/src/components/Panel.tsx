import type { ReactNode } from "react";

type Tone = "neutral" | "danger" | "warning" | "success" | "accent";

const toneRing: Record<Tone, string> = {
  neutral: "border-white/5",
  danger: "border-red-500/20",
  warning: "border-amber-400/20",
  success: "border-emerald-500/20",
  accent: "border-white/10",
};

const toneValue: Record<Tone, string> = {
  neutral: "text-zinc-100",
  danger: "text-red-400",
  warning: "text-amber-300",
  success: "text-emerald-400",
  accent: "text-amber-300",
};

export function StatCard({
  label,
  value,
  hint,
  tone = "neutral",
  children,
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  tone?: Tone;
  children?: ReactNode;
}) {
  return (
    <div className={`rounded-xl border bg-[#111114] p-4 ${toneRing[tone]}`}>
      <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-zinc-500">
        {label}
      </p>
      <p className={`mt-2 text-2xl font-semibold tabular-nums ${toneValue[tone]}`}>{value}</p>
      {hint ? <p className="mt-1 text-xs text-zinc-500">{hint}</p> : null}
      {children}
    </div>
  );
}

export function Panel({
  title,
  subtitle,
  action,
  children,
  className = "",
}: {
  title?: string;
  subtitle?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`rounded-xl border border-white/5 bg-[#111114] ${className}`}>
      {(title || action) && (
        <header className="flex flex-wrap items-start justify-between gap-3 border-b border-white/5 px-4 py-3.5 sm:px-5">
          <div>
            {title ? <h2 className="text-sm font-semibold text-zinc-100">{title}</h2> : null}
            {subtitle ? <p className="mt-0.5 text-xs text-zinc-500">{subtitle}</p> : null}
          </div>
          {action}
        </header>
      )}
      {children}
    </section>
  );
}
