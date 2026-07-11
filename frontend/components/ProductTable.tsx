"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { SortableHeader } from "@/components/SortableHeader";
import { dateTime, titleCase } from "@/lib/format";
import { nextProductSort, sortProducts, type ProductSortKey, type ProductSortState } from "@/lib/product-sort";
import type { ProductListItem } from "@/types/api";
import { DecisionBadge } from "./validation/ValidationCard";
import { RecommendationBadge } from "./RecommendationBadge";
import { ScoreBadge } from "./ScoreBadge";

export function ProductTable({ products }: { products: ProductListItem[] }) {
  const [sort, setSort] = useState<ProductSortState>(null);
  const sortedProducts = useMemo(() => sortProducts(products, sort), [products, sort]);
  const onSort = (key: ProductSortKey) => setSort((current) => nextProductSort(current, key));

  return (
    <div className="overflow-x-auto border border-terminal-line bg-terminal-bg">
      <table className="w-full min-w-[1180px] border-collapse text-left text-sm">
        <thead className="bg-terminal-panel text-xs uppercase text-terminal-muted">
          <tr>
            <SortableHeader label="Product" sortKey="product" sort={sort} onSort={onSort} />
            <SortableHeader label="Category" sortKey="category" sort={sort} onSort={onSort} />
            <SortableHeader label="Score" sortKey="score" sort={sort} onSort={onSort} />
            <SortableHeader label="Eligible" sortKey="eligible" sort={sort} onSort={onSort} />
            <SortableHeader label="Validation" sortKey="validation" sort={sort} onSort={onSort} />
            <SortableHeader label="Economics" sortKey="economics" sort={sort} onSort={onSort} />
            <SortableHeader label="Supplier" sortKey="supplier" sort={sort} onSort={onSort} />
            <SortableHeader label="Evidence" sortKey="evidence" sort={sort} onSort={onSort} />
            <SortableHeader label="Missing" sortKey="missing" sort={sort} onSort={onSort} />
            <SortableHeader label="Recommendation" sortKey="recommendation" sort={sort} onSort={onSort} />
            <SortableHeader label="Updated" sortKey="updated" sort={sort} onSort={onSort} />
          </tr>
        </thead>
        <tbody>
          {sortedProducts.map((product) => (
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
