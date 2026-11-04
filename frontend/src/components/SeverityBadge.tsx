import type { Severity } from "../types";
import { severityDot, severityStyles } from "../lib/format";

export function SeverityBadge({
  severity,
  size = "sm",
}: {
  severity: Severity;
  size?: "sm" | "md";
}) {
  const sizing = size === "md" ? "px-3 py-1 text-xs" : "px-2.5 py-0.5 text-[11px]";
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border font-semibold uppercase tracking-wide ${sizing} ${severityStyles[severity]}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${severityDot[severity]}`} />
      {severity}
    </span>
  );
}
