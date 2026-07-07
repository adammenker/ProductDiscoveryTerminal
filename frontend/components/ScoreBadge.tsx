import clsx from "clsx";
import { formatScore } from "@/lib/format";

export function ScoreBadge({ value, compact = false }: { value?: number | null; compact?: boolean }) {
  const score = value ?? null;
  const tone =
    score === null
      ? "border-terminal-line text-terminal-muted"
      : score >= 85
        ? "border-terminal-green/70 bg-terminal-green/10 text-terminal-green"
        : score >= 70
          ? "border-terminal-cyan/70 bg-terminal-cyan/10 text-terminal-cyan"
          : score >= 50
            ? "border-terminal-amber/70 bg-terminal-amber/10 text-terminal-amber"
            : "border-terminal-rose/70 bg-terminal-rose/10 text-terminal-rose";

  return (
    <span
      className={clsx(
        "inline-flex items-center justify-center border font-mono font-semibold tabular-nums",
        compact ? "h-7 min-w-12 px-2 text-xs" : "h-12 min-w-16 px-3 text-lg",
        tone
      )}
    >
      {formatScore(score)}
    </span>
  );
}

