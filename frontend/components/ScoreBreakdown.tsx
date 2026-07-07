import type { ScoreRecord } from "@/types/api";

const rows: Array<{ key: keyof ScoreRecord; label: string; inverse?: boolean }> = [
  { key: "demand_score", label: "Demand" },
  { key: "growth_score", label: "Growth" },
  { key: "competition_score", label: "Competition" },
  { key: "margin_score", label: "Margin" },
  { key: "pain_point_score", label: "Pain" },
  { key: "risk_score", label: "Risk", inverse: true },
  { key: "confidence_score", label: "Confidence" }
];

export function ScoreBreakdown({ score }: { score: ScoreRecord }) {
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

