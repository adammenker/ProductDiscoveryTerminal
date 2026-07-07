import clsx from "clsx";
import { recommendationLabel } from "@/lib/format";
import type { Recommendation } from "@/types/api";

export function RecommendationBadge({ value }: { value?: Recommendation | string | null }) {
  const tone =
    value === "strong_opportunity" || value === "investigate"
      ? "border-terminal-green/60 bg-terminal-green/10 text-terminal-green"
      : value === "watch"
        ? "border-terminal-amber/60 bg-terminal-amber/10 text-terminal-amber"
        : value === "skip"
          ? "border-terminal-rose/60 bg-terminal-rose/10 text-terminal-rose"
          : "border-terminal-line bg-terminal-panel text-terminal-muted";

  return (
    <span className={clsx("inline-flex h-7 items-center border px-2 font-mono text-xs", tone)}>
      {recommendationLabel(value)}
    </span>
  );
}

