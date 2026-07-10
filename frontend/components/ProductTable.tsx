import Link from "next/link";
import { dateTime, titleCase } from "@/lib/format";
import type { ProductListItem } from "@/types/api";
import { DecisionBadge } from "./validation/ValidationCard";
import { RecommendationBadge } from "./RecommendationBadge";
import { ScoreBadge } from "./ScoreBadge";

export function ProductTable({ products }: { products: ProductListItem[] }) {
  return (
    <div className="overflow-x-auto border border-terminal-line bg-terminal-bg">
      <table className="w-full min-w-[1180px] border-collapse text-left text-sm">
        <thead className="bg-terminal-panel text-xs uppercase text-terminal-muted">
          <tr>
            <th className="border-b border-terminal-line px-3 py-2 font-mono font-medium">Product</th>
            <th className="border-b border-terminal-line px-3 py-2 font-mono font-medium">Category</th>
            <th className="border-b border-terminal-line px-3 py-2 font-mono font-medium">Score</th>
            <th className="border-b border-terminal-line px-3 py-2 font-mono font-medium">Eligible</th>
            <th className="border-b border-terminal-line px-3 py-2 font-mono font-medium">Validation</th>
            <th className="border-b border-terminal-line px-3 py-2 font-mono font-medium">Economics</th>
            <th className="border-b border-terminal-line px-3 py-2 font-mono font-medium">Supplier</th>
            <th className="border-b border-terminal-line px-3 py-2 font-mono font-medium">Evidence</th>
            <th className="border-b border-terminal-line px-3 py-2 font-mono font-medium">Missing</th>
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
              <td className="px-3 py-2 font-mono text-xs">
                {product.constraint_eligible === null ? (
                  <span className="text-terminal-muted">Unknown</span>
                ) : product.constraint_eligible ? (
                  <span className="text-terminal-green">Pass</span>
                ) : (
                  <span className="text-terminal-rose">Fail</span>
                )}
              </td>
              <td className="px-3 py-2"><DecisionBadge value={product.validation_decision} /></td>
              <td className="px-3 py-2 font-mono text-xs text-terminal-muted">{titleCase(product.economics_decision)}</td>
              <td className="px-3 py-2 font-mono text-xs text-terminal-muted">{titleCase(product.supplier_validation_decision)}</td>
              <td className="px-3 py-2 font-mono text-xs tabular-nums">{product.cross_source_confidence_score?.toFixed(0) ?? "--"}</td>
              <td className="px-3 py-2 font-mono text-xs text-terminal-amber">{product.missing_evidence.length || "--"}</td>
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
