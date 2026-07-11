import type { ScoreRecord } from "@/types/api";
import { titleCase } from "@/lib/format";

const rows: Array<{ key: keyof ScoreRecord; label: string; inverse?: boolean }> = [
  { key: "demand_score", label: "Demand Proxy" },
  { key: "growth_score", label: "Growth" },
  { key: "competition_score", label: "Competition" },
  { key: "margin_score", label: "Margin" },
  { key: "pain_point_score", label: "Pain" },
  { key: "risk_score", label: "Risk", inverse: true },
  { key: "confidence_score", label: "Confidence" }
];

export function ScoreBreakdown({ score }: { score: ScoreRecord }) {
  const components = score.components ?? score.score_breakdown.components;
  if (components && Object.keys(components).length) {
    return (
      <div className="space-y-3">
        <div className="grid gap-2 sm:grid-cols-3">
          <MiniScore label="Opportunity" value={score.opportunity_score ?? score.final_score} />
          <MiniScore label="Confidence" value={score.evidence_confidence_score ?? score.confidence_score} />
          <MiniScore label="Readiness" value={score.validation_readiness_score} />
        </div>
        <div className="space-y-2">
          {Object.values(components).map((component) => (
            <div key={component.name} className="border border-terminal-line bg-terminal-bg p-3">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="font-mono text-xs uppercase text-terminal-muted">
                    {titleCase(component.name)}
                  </div>
                  <div className="mt-1 text-xs text-terminal-muted">{component.explanation}</div>
                </div>
                <div className="text-right">
                  <div className="font-mono text-sm tabular-nums">{component.value === null ? "--" : component.value.toFixed(0)}</div>
                  <div className="mt-1 font-mono text-[10px] uppercase text-terminal-muted">
                    {titleCase(component.status)}
                  </div>
                </div>
              </div>
              <div className="mt-2 grid gap-2 sm:grid-cols-2">
                <Bar label="Coverage" value={component.coverage} />
                <Bar label="Confidence" value={component.confidence} />
              </div>
              {component.warnings.length ? (
                <div className="mt-2 text-xs text-terminal-amber">{component.warnings.join(" / ")}</div>
              ) : null}
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {rows.map((row) => {
        const value = Number(score[row.key] ?? 0);
        const color = row.inverse
          ? value >= 60
            ? "bg-terminal-rose"
            : value >= 35
              ? "bg-terminal-amber"
              : "bg-terminal-green"
          : value >= 70
            ? "bg-terminal-green"
            : value >= 50
              ? "bg-terminal-amber"
              : "bg-terminal-rose";
        return (
          <div key={row.key} className="grid grid-cols-[112px_1fr_52px] items-center gap-3 text-sm">
            <div className="font-mono text-xs uppercase text-terminal-muted">{row.label}</div>
            <div className="h-2 overflow-hidden bg-terminal-line">
              <div className={`${color} h-full`} style={{ width: `${Math.min(100, Math.max(0, value))}%` }} />
            </div>
            <div className="text-right font-mono text-xs tabular-nums">{value.toFixed(0)}</div>
          </div>
        );
      })}
    </div>
  );
}

function MiniScore({ label, value }: { label: string; value?: number | null }) {
  return (
    <div className="border border-terminal-line bg-terminal-bg p-2">
      <div className="font-mono text-[10px] uppercase text-terminal-muted">{label}</div>
      <div className="mt-1 font-mono text-lg tabular-nums">{value == null ? "--" : value.toFixed(0)}</div>
    </div>
  );
}

function Bar({ label, value }: { label: string; value: number }) {
  return (
    <div className="grid grid-cols-[76px_1fr_36px] items-center gap-2 text-xs">
      <div className="font-mono uppercase text-terminal-muted">{label}</div>
      <div className="h-1.5 bg-terminal-line">
        <div className="h-full bg-terminal-green" style={{ width: `${Math.min(100, Math.max(0, value))}%` }} />
      </div>
      <div className="text-right font-mono tabular-nums">{value.toFixed(0)}</div>
    </div>
  );
}
