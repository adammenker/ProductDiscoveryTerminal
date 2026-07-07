import Link from "next/link";
import { titleCase } from "@/lib/format";
import type { ProductListItem } from "@/types/api";
import { RecommendationBadge } from "./RecommendationBadge";
import { ScoreBadge } from "./ScoreBadge";

export function OpportunityCard({ product }: { product: ProductListItem }) {
  return (
    <article className="border border-terminal-line bg-terminal-panel/90 p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <Link href={`/products/${product.id}`} className="block truncate text-base font-semibold hover:text-terminal-green">
            {titleCase(product.canonical_name)}
          </Link>
          <div className="mt-1 text-xs uppercase text-terminal-muted">{titleCase(product.category)}</div>
        </div>
        <ScoreBadge value={product.latest_score} />
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <RecommendationBadge value={product.recommendation} />
        <span className="font-mono text-xs text-terminal-muted">D {product.demand_score?.toFixed(0) ?? "--"}</span>
        <span className="font-mono text-xs text-terminal-muted">M {product.margin_score?.toFixed(0) ?? "--"}</span>
        <span className="font-mono text-xs text-terminal-muted">R {product.risk_score?.toFixed(0) ?? "--"}</span>
      </div>
      <p className="mt-3 line-clamp-3 text-sm leading-6 text-terminal-muted">{product.explanation}</p>
    </article>
  );
}

