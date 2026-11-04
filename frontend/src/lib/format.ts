import type { Severity } from "../types";

export const SEVERITY_ORDER: Severity[] = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];

export const severityStyles: Record<Severity, string> = {
  CRITICAL: "border-red-500/30 bg-red-500/10 text-red-300",
  HIGH: "border-orange-500/30 bg-orange-500/10 text-orange-300",
  MEDIUM: "border-amber-400/30 bg-amber-400/10 text-amber-200",
  LOW: "border-emerald-500/25 bg-emerald-500/10 text-emerald-300",
};

export const severityDot: Record<Severity, string> = {
  CRITICAL: "bg-red-500",
  HIGH: "bg-orange-500",
  MEDIUM: "bg-amber-400",
  LOW: "bg-emerald-500",
};

export function fmtNumber(value: number, digits = 0): string {
  return value.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function fmtPct(value: number, digits = 0): string {
  return `${(value * 100).toFixed(digits)}%`;
}

export function fmtDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function timeAgo(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  const seconds = Math.max(0, Math.round((Date.now() - date.getTime()) / 1000));
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

export function rulTone(rul: number): string {
  if (rul <= 15) return "bg-red-500";
  if (rul <= 30) return "bg-orange-500";
  if (rul <= 60) return "bg-amber-400";
  return "bg-emerald-500";
}
