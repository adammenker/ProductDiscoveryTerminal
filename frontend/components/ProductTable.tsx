import Link from "next/link";
import { dateTime, titleCase } from "@/lib/format";
import type { ProductListItem } from "@/types/api";
import { RecommendationBadge } from "./RecommendationBadge";
import { ScoreBadge } from "./ScoreBadge";

export function ProductTable({ products }: { products: ProductListItem[] }) {
  return (
    <div className="overflow-x-auto border border-terminal-line bg-terminal-bg">
      <table className="w-full min-w-[980px] border-collapse text-left text-sm">
        <thead className="bg-terminal-panel text-xs uppercase text-terminal-muted">
          <tr>
            <th className="border-b border-terminal-line px-3 py-2 font-mono font-medium">Product</th>
            <th className="border-b border-terminal-line px-3 py-2 font-mono font-medium">Category</th>
            <th className="border-b border-terminal-line px-3 py-2 font-mono font-medium">Score</th>
            <th className="border-b border-terminal-line px-3 py-2 font-mono font-medium">Demand</th>
            <th className="border-b border-terminal-line px-3 py-2 font-mono font-medium">Growth</th>
            <th className="border-b border-terminal-line px-3 py-2 font-mono font-medium">Margin</th>
            <th className="border-b border-terminal-line px-3 py-2 font-mono font-medium">Risk</th>
            <th className="border-b border-terminal-line px-3 py-2 font-mono font-medium">Recommendation</th>
            <th className="border-b border-terminal-line px-3 py-2 font-mono font-medium">Updated</th>
          </tr>
        </thead>
        <tbody>
          {products.map((product) => (
            <tr key={product.id} className="border-b border-terminal-line/70 hover:bg-terminal-panel/70">
              <td className="px-3 py-2">
                <Link href={`/products/${product.id}`} className="font-medium text-terminal-ink hover:text-terminal-green">
                  {titleCase(product.canonical_name)}
                </Link>
              </td>
              <td className="px-3 py-2 text-terminal-muted">{titleCase(product.category)}</td>
              <td className="px-3 py-2">
                <ScoreBadge value={product.latest_score} compact />
              </td>
              <td className="px-3 py-2 font-mono text-xs tabular-nums">{product.demand_score?.toFixed(0) ?? "--"}</td>
              <td className="px-3 py-2 font-mono text-xs tabular-nums">{product.growth_score?.toFixed(0) ?? "--"}</td>
              <td className="px-3 py-2 font-mono text-xs tabular-nums">{product.margin_score?.toFixed(0) ?? "--"}</td>
              <td className="px-3 py-2 font-mono text-xs tabular-nums">{product.risk_score?.toFixed(0) ?? "--"}</td>
              <td className="px-3 py-2">
                <RecommendationBadge value={product.recommendation} />
              </td>
              <td className="px-3 py-2 font-mono text-xs text-terminal-muted">{dateTime(product.updated_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

