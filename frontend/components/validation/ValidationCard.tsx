import clsx from "clsx";
import { AlertTriangle, CheckCircle2, Clock3, Database, MinusCircle } from "lucide-react";
import { dateTime, titleCase } from "@/lib/format";
import type { EvidenceRow, ValidationDecision } from "@/types/api";

export function ValidationCard({
  title,
  source,
  updatedAt,
  confidence,
  missing = [],
  action,
  children
}: {
  title: string;
  source?: string | null;
  updatedAt?: string | null;
  confidence?: number | string | null;
  missing?: string[];
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  const confidenceLabel =
    confidence === null || confidence === undefined
      ? "Confidence --"
      : typeof confidence === "number"
        ? `Confidence ${(confidence <= 1 ? confidence * 100 : confidence).toFixed(0)}%`
        : `Confidence ${titleCase(confidence)}`;

  return (
    <section className="border border-terminal-line bg-terminal-panel/80">
      <div className="flex flex-col gap-3 border-b border-terminal-line px-4 py-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="font-mono text-xs uppercase tracking-[0.18em] text-terminal-ink">{title}</h2>
          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 font-mono text-[11px] text-terminal-muted">
            <span className="inline-flex items-center gap-1.5">
              <Database size={12} />
              {source ? titleCase(source) : "Source unavailable"}
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Clock3 size={12} />
              {updatedAt ? dateTime(updatedAt) : "Not updated"}
            </span>
            <span>{confidenceLabel}</span>
          </div>
        </div>
        {action}
      </div>
      <div className="p-4">{children}</div>
      {missing.length ? (
        <div className="border-t border-terminal-amber/30 bg-terminal-amber/5 px-4 py-3">
          <div className="flex items-start gap-2 text-xs text-terminal-amber">
            <AlertTriangle size={14} className="mt-0.5 shrink-0" />
            <span>Missing: {missing.join(" / ")}</span>
          </div>
        </div>
      ) : null}
    </section>
  );
}

export function DecisionBadge({ value }: { value?: ValidationDecision | string | null }) {
  const tone =
    value === "pursue" || value === "quote_at_or_below_ceiling"
      ? "border-terminal-green/60 bg-terminal-green/10 text-terminal-green"
      : value === "skip" || value === "quote_above_ceiling"
        ? "border-terminal-rose/60 bg-terminal-rose/10 text-terminal-rose"
        : value === "investigate" || value === "needs_supplier_quote"
          ? "border-terminal-amber/60 bg-terminal-amber/10 text-terminal-amber"
          : "border-terminal-line bg-terminal-bg text-terminal-muted";

  return (
    <span className={clsx("inline-flex h-7 items-center border px-2 font-mono text-xs uppercase", tone)}>
      {value ? titleCase(value) : "No decision"}
    </span>
  );
}

export function WarningList({ warnings }: { warnings: string[] }) {
  if (!warnings.length) return null;
  return (
    <div className="space-y-2 border border-terminal-amber/40 bg-terminal-amber/5 p-3">
      {warnings.map((warning) => (
        <div key={warning} className="flex items-start gap-2 text-xs leading-5 text-terminal-amber">
          <AlertTriangle size={14} className="mt-0.5 shrink-0" />
          <span>{warning}</span>
        </div>
      ))}
    </div>
  );
}

export function EvidenceMatrixTable({ rows }: { rows: EvidenceRow[] }) {
  if (!rows.length) {
    return <div className="border border-terminal-line bg-terminal-bg p-4 text-sm text-terminal-muted">No evidence rows available.</div>;
  }

  return (
    <div className="overflow-x-auto border border-terminal-line bg-terminal-bg">
      <table className="w-full min-w-[720px] border-collapse text-left text-sm">
        <thead className="bg-terminal-panel font-mono text-xs uppercase text-terminal-muted">
          <tr>
            <th className="border-b border-terminal-line px-3 py-2 font-medium">Evidence</th>
            <th className="border-b border-terminal-line px-3 py-2 font-medium">Signal</th>
            <th className="border-b border-terminal-line px-3 py-2 font-medium">Sources</th>
            <th className="border-b border-terminal-line px-3 py-2 font-medium">Confidence</th>
            <th className="border-b border-terminal-line px-3 py-2 font-medium">Notes</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const Icon =
              row.direction === "positive" ? CheckCircle2 : row.direction === "negative" ? AlertTriangle : MinusCircle;
            return (
              <tr key={row.area} className="border-b border-terminal-line/70 last:border-b-0">
                <td className="px-3 py-2 font-medium">{row.area}</td>
                <td className="px-3 py-2">
                  <span
                    className={clsx(
                      "inline-flex items-center gap-1.5 font-mono text-xs uppercase",
                      row.direction === "positive"
                        ? "text-terminal-green"
                        : row.direction === "negative"
                          ? "text-terminal-rose"
                          : "text-terminal-amber"
                    )}
                  >
                    <Icon size={13} />
                    {row.signal}
                  </span>
                </td>
                <td className="px-3 py-2 font-mono text-xs tabular-nums">{row.source_count}</td>
                <td className="px-3 py-2 font-mono text-xs tabular-nums">{row.confidence}%</td>
                <td className="max-w-[420px] px-3 py-2 text-terminal-muted">{row.notes}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function ValidationWarnings() {
  return (
    <div className="grid gap-2 border-y border-terminal-line py-3 text-xs text-terminal-muted md:grid-cols-2">
      <span>Amazon fees may be estimates derived from comparable ASINs.</span>
      <span>Supplier quotes are user-provided unless their source states otherwise.</span>
      <span>Product Opportunity Explorer data is manual import only.</span>
      <span>No automatic buy, sell, or sourcing decision is executed.</span>
    </div>
  );
}
