import type { ReactNode } from "react";
import { RefreshIcon } from "./icons";

export function LoadingBlock({ rows = 4, label = "Loading" }: { rows?: number; label?: string }) {
  return (
    <div className="space-y-3 p-5" aria-busy="true" aria-label={label}>
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="skeleton h-10 rounded-lg" />
      ))}
    </div>
  );
}

export function ErrorBlock({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="flex flex-col items-start gap-3 p-6">
      <div className="rounded-lg border border-red-500/25 bg-red-500/5 px-4 py-3">
        <p className="text-sm font-medium text-red-300">Could not load data</p>
        <p className="mt-1 max-w-2xl break-words text-xs text-red-200/70">{message}</p>
      </div>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="inline-flex items-center gap-2 rounded-lg border border-white/10 px-3 py-1.5 text-xs font-medium text-zinc-300 transition hover:border-white/20 hover:text-white"
        >
          <RefreshIcon className="h-3.5 w-3.5" />
          Retry
        </button>
      ) : null}
    </div>
  );
}

export function EmptyBlock({
  title,
  hint,
  action,
}: {
  title: string;
  hint?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-6 py-14 text-center">
      <p className="text-sm font-medium text-zinc-300">{title}</p>
      {hint ? <p className="max-w-md text-xs text-zinc-500">{hint}</p> : null}
      {action}
    </div>
  );
}
