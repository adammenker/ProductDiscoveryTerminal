"use client";

import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { useMemo, useState } from "react";
import { EmptyState } from "@/components/EmptyState";
import { ProductTable } from "@/components/ProductTable";
import { api } from "@/lib/api";

export default function ProductsPage() {
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [recommendation, setRecommendation] = useState("");
  const [minScore, setMinScore] = useState("");
  const [eligibility, setEligibility] = useState("");
  const [validationDecision, setValidationDecision] = useState("");

  const filters = useMemo(
    () => ({
      q,
      category,
      recommendation,
      eligible: eligibility === "" ? undefined : eligibility === "eligible",
      validation_decision: validationDecision,
      min_score: minScore ? Number(minScore) : undefined,
      limit: 100
    }),
    [category, eligibility, minScore, q, recommendation, validationDecision]
  );

  const products = useQuery({
    queryKey: ["products", filters],
    queryFn: () => api.products(filters)
  });

  const items = products.data?.items ?? [];

  return (
    <div className="space-y-5">
      <div className="border-b border-terminal-line pb-5">
        <div className="font-mono text-xs uppercase tracking-[0.24em] text-terminal-green">Products</div>
        <h1 className="mt-2 text-2xl font-semibold">Candidate search</h1>
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-[1fr_160px_180px_160px_160px_120px]">
        <label className="relative block">
          <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-terminal-muted" />
          <input
            value={q}
            onChange={(event) => setQ(event.target.value)}
            placeholder="Search product or alias"
            className="h-10 w-full border border-terminal-line bg-terminal-panel pl-9 pr-3 text-sm outline-none transition placeholder:text-terminal-muted focus:border-terminal-green"
          />
        </label>
        <select
          value={category}
          onChange={(event) => setCategory(event.target.value)}
          className="h-10 border border-terminal-line bg-terminal-panel px-3 text-sm outline-none focus:border-terminal-green"
        >
          <option value="">All categories</option>
          <option value="beauty">Beauty</option>
          <option value="home">Home</option>
          <option value="pets">Pets</option>
          <option value="kitchen">Kitchen</option>
          <option value="health">Health</option>
          <option value="travel">Travel</option>
        </select>
        <select
          value={recommendation}
          onChange={(event) => setRecommendation(event.target.value)}
          className="h-10 border border-terminal-line bg-terminal-panel px-3 text-sm outline-none focus:border-terminal-green"
        >
          <option value="">All recommendations</option>
          <option value="strong_opportunity">Strong Opportunity</option>
          <option value="investigate">Investigate</option>
          <option value="watch">Watch</option>
          <option value="needs_more_data">Needs More Data</option>
          <option value="skip">Skip</option>
        </select>
        <select
          value={eligibility}
          onChange={(event) => setEligibility(event.target.value)}
          className="h-10 border border-terminal-line bg-terminal-panel px-3 text-sm outline-none focus:border-terminal-green"
        >
          <option value="">All eligibility</option>
          <option value="eligible">Eligible</option>
          <option value="ineligible">Ineligible</option>
        </select>
        <select
          value={validationDecision}
          onChange={(event) => setValidationDecision(event.target.value)}
          className="h-10 border border-terminal-line bg-terminal-panel px-3 text-sm outline-none focus:border-terminal-green"
        >
          <option value="">All decisions</option>
          <option value="pursue">Pursue</option>
          <option value="investigate">Investigate</option>
          <option value="watch">Watch</option>
          <option value="skip">Skip</option>
        </select>
        <input
          value={minScore}
          onChange={(event) => setMinScore(event.target.value)}
          inputMode="numeric"
          placeholder="Min score"
          className="h-10 border border-terminal-line bg-terminal-panel px-3 text-sm outline-none placeholder:text-terminal-muted focus:border-terminal-green"
        />
      </div>

      {products.isLoading ? (
        <EmptyState label="Loading products" />
      ) : items.length ? (
        <ProductTable products={items} />
      ) : (
        <EmptyState label="No products match the current filters" />
      )}
    </div>
  );
}
