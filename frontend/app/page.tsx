"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, ExternalLink, Loader2, Search } from "lucide-react";
import Link from "next/link";
import { type FormEvent, useState } from "react";
import { EmptyState } from "@/components/EmptyState";
import { PluginRunTable } from "@/components/PluginRunTable";
import { DecisionBadge } from "@/components/validation/ValidationCard";
import { api } from "@/lib/api";
import { formatScore, titleCase } from "@/lib/format";
import type { ProductListItem, ProductResearchResponse } from "@/types/api";

export default function DashboardPage() {
  const queryClient = useQueryClient();
  const [term, setTerm] = useState("");

  const productsQuery = useQuery({
    queryKey: ["opportunities", { limit: 100, validation: true }],
    queryFn: () => api.opportunities({ limit: 100 })
  });

  const research = useMutation({
    mutationFn: (query: string) => api.researchProduct({ query }),
    onSuccess: async (result) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["opportunities"] }),
        queryClient.invalidateQueries({ queryKey: ["products"] }),
        queryClient.invalidateQueries({ queryKey: ["plugin-runs"] }),
        queryClient.invalidateQueries({ queryKey: ["product", result.product_id] })
      ]);
    }
  });

  const products = productsQuery.data?.items ?? [];
  const metrics = buildMetrics(products);
  const canSubmit = term.trim().length >= 2 && !research.isPending;

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const query = term.trim();
    if (query.length < 2) return;
    research.mutate(query);
  }

  return (
    <div className="space-y-6">
      <header className="border-b border-terminal-line pb-5">
        <div className="font-mono text-xs uppercase tracking-[0.24em] text-terminal-green">
          Product Discovery Terminal
        </div>
        <h1 className="mt-2 text-2xl font-semibold">Amazon product research</h1>
      </header>

      <section className="border border-terminal-line bg-terminal-panel/70 p-4">
        <form onSubmit={onSubmit} className="grid gap-3 lg:grid-cols-[1fr_auto] lg:items-end">
          <label className="block">
            <span className="mb-2 block font-mono text-xs uppercase tracking-[0.18em] text-terminal-muted">
              Product name
            </span>
            <input
              value={term}
              onChange={(event) => setTerm(event.target.value)}
              placeholder="silicone sink strainer"
              className="h-11 w-full border border-terminal-line bg-terminal-bg px-3 text-sm text-terminal-ink outline-none placeholder:text-terminal-muted focus:border-terminal-green"
            />
          </label>
          <button
            type="submit"
            disabled={!canSubmit}
            className="inline-flex h-11 items-center justify-center gap-2 border border-terminal-green/70 bg-terminal-green/10 px-4 font-mono text-xs uppercase tracking-[0.14em] text-terminal-green transition hover:bg-terminal-green/15 disabled:cursor-not-allowed disabled:border-terminal-line disabled:bg-terminal-bg disabled:text-terminal-muted"
          >
            {research.isPending ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
            Fetch + Score
          </button>
        </form>

        <ResearchStatus result={research.data} error={research.error} isPending={research.isPending} />
      </section>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Metric label="Scored products" value={productsQuery.data?.total ?? 0} />
        <Metric label="Pursue" value={metrics.pursue} tone="green" />
        <Metric label="Needs quote" value={metrics.needsQuote} tone="amber" />
        <Metric label="Blocked" value={metrics.blocked} tone="rose" />
      </div>

      {productsQuery.isError ? (
        <div className="border border-terminal-rose/50 bg-terminal-rose/5 p-3 text-sm text-terminal-rose">
          Product data unavailable: {productsQuery.error.message}
        </div>
      ) : null}

      <section>
        <SectionTitle title="Scored products" />
        <ProductTable
          products={products}
          isLoading={productsQuery.isLoading}
          activeProductId={research.data?.product_id}
        />
      </section>

      {research.data?.pipeline.plugin_runs.length ? (
        <section>
          <SectionTitle title="Last research run" />
          <PluginRunTable runs={research.data.pipeline.plugin_runs} />
        </section>
      ) : null}

      <div className="flex items-start gap-2 border border-terminal-amber/40 bg-terminal-amber/5 px-3 py-2 text-xs text-terminal-amber">
        <AlertTriangle size={14} className="mt-0.5 shrink-0" />
        <span>Scores are validation guidance only. No automatic buy, sell, or sourcing action is executed.</span>
      </div>
    </div>
  );
}

function ResearchStatus({
  result,
  error,
  isPending
}: {
  result?: ProductResearchResponse;
  error: Error | null;
  isPending: boolean;
}) {
  if (isPending) {
    return (
      <div className="mt-4 border border-terminal-line bg-terminal-bg px-3 py-2 font-mono text-xs uppercase tracking-[0.14em] text-terminal-muted">
        Running SP-API pipeline
      </div>
    );
  }

  if (error) {
    return (
      <div className="mt-4 border border-terminal-rose/50 bg-terminal-rose/5 px-3 py-2 text-sm text-terminal-rose">
        {error.message}
      </div>
    );
  }

  if (!result) return null;

  const pipeline = result.pipeline;
  const hasErrors = pipeline.errors.length > 0 || pipeline.status !== "success";
  const tone = hasErrors
    ? "border-terminal-amber/50 bg-terminal-amber/5 text-terminal-amber"
    : "border-terminal-green/50 bg-terminal-green/5 text-terminal-green";

  return (
    <div className={`mt-4 border px-3 py-3 ${tone}`}>
      <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <div className="text-sm font-medium">{titleCase(result.canonical_name)}</div>
          <div className="mt-1 font-mono text-[11px] uppercase tracking-[0.12em]">
            {titleCase(pipeline.status)} / {pipeline.observations_created} observations / {pipeline.scores_updated} scores
          </div>
        </div>
        <Link
          href={`/products/${result.product_id}`}
          className="inline-flex h-9 items-center justify-center gap-2 border border-current px-3 font-mono text-xs uppercase tracking-[0.12em]"
        >
          Open product
          <ExternalLink size={14} />
        </Link>
      </div>
      {pipeline.errors.length ? (
        <div className="mt-3 space-y-1 border-t border-current/20 pt-2 text-xs">
          {pipeline.errors.slice(0, 4).map((message) => (
            <div key={message}>{message}</div>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function ProductTable({
  products,
  isLoading,
  activeProductId
}: {
  products: ProductListItem[];
  isLoading: boolean;
  activeProductId?: string;
}) {
  if (isLoading) {
    return <EmptyState label="Loading products" />;
  }

  if (!products.length) {
    return <EmptyState label="No products scored yet" />;
  }

  return (
    <div className="overflow-x-auto border border-terminal-line bg-terminal-bg">
      <table className="w-full min-w-[760px] border-collapse text-left text-sm">
        <thead className="bg-terminal-panel text-xs uppercase text-terminal-muted">
          <tr>
            <th className="border-b border-terminal-line px-3 py-2 font-mono font-medium">Product</th>
            <th className="border-b border-terminal-line px-3 py-2 font-mono font-medium">Score</th>
            <th className="border-b border-terminal-line px-3 py-2 font-mono font-medium">Decision</th>
            <th className="border-b border-terminal-line px-3 py-2 font-mono font-medium">Economics</th>
            <th className="border-b border-terminal-line px-3 py-2 font-mono font-medium">Evidence</th>
            <th className="border-b border-terminal-line px-3 py-2 font-mono font-medium" aria-label="Open" />
          </tr>
        </thead>
        <tbody>
          {products.map((product) => (
            <tr
              key={product.id}
              className={
                product.id === activeProductId
                  ? "border-b border-terminal-green/40 bg-terminal-green/5"
                  : "border-b border-terminal-line/70"
              }
            >
              <td className="px-3 py-3">
                <div className="font-medium">{titleCase(product.canonical_name)}</div>
                <div className="mt-1 font-mono text-[11px] uppercase tracking-[0.1em] text-terminal-muted">
                  {titleCase(product.category)}
                </div>
              </td>
              <td className="px-3 py-3 font-mono text-sm tabular-nums">{formatScore(product.latest_score)}</td>
              <td className="px-3 py-3">
                <DecisionBadge value={product.validation_decision ?? product.recommendation} />
              </td>
              <td className="px-3 py-3">
                <DecisionBadge value={product.economics_decision ?? product.supplier_validation_decision} />
              </td>
              <td className="px-3 py-3">
                <div className="font-mono text-xs tabular-nums">
                  {formatScore(product.cross_source_confidence_score)}
                </div>
                {product.missing_evidence.length ? (
                  <div className="mt-1 text-xs text-terminal-amber">
                    {product.missing_evidence.length} missing
                  </div>
                ) : (
                  <div className="mt-1 text-xs text-terminal-muted">Complete</div>
                )}
              </td>
              <td className="px-3 py-3">
                <Link
                  href={`/products/${product.id}`}
                  aria-label={`Open ${titleCase(product.canonical_name)}`}
                  className="inline-flex h-8 w-8 items-center justify-center border border-terminal-line text-terminal-muted hover:border-terminal-green hover:text-terminal-green"
                >
                  <ExternalLink size={14} />
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function buildMetrics(products: ProductListItem[]) {
  return {
    pursue: products.filter((product) => product.validation_decision === "pursue").length,
    needsQuote: products.filter(
      (product) =>
        product.supplier_validation_decision === "needs_supplier_quote" ||
        product.economics_decision === "needs_supplier_quote"
    ).length,
    blocked: products.filter(
      (product) =>
        product.constraint_eligible === false ||
        product.validation_decision === "skip" ||
        product.economics_decision === "quote_above_ceiling" ||
        product.supplier_validation_decision === "quote_above_ceiling"
    ).length
  };
}

function Metric({
  label,
  value,
  tone = "neutral"
}: {
  label: string;
  value: number;
  tone?: "neutral" | "green" | "amber" | "rose";
}) {
  const color =
    tone === "green"
      ? "text-terminal-green"
      : tone === "amber"
        ? "text-terminal-amber"
        : tone === "rose"
          ? "text-terminal-rose"
          : "text-terminal-ink";
  return (
    <div className="border border-terminal-line bg-terminal-panel/80 p-3">
      <div className="font-mono text-[11px] uppercase text-terminal-muted">{label}</div>
      <div className={`mt-1 font-mono text-xl tabular-nums ${color}`}>{value}</div>
    </div>
  );
}

function SectionTitle({ title }: { title: string }) {
  return <h2 className="mb-3 font-mono text-xs uppercase tracking-[0.18em] text-terminal-muted">{title}</h2>;
}
