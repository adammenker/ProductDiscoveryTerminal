"use client";

import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, ArrowRight, CheckCircle2, Clock3, SearchX, Store, XCircle } from "lucide-react";
import Link from "next/link";
import { EmptyState } from "@/components/EmptyState";
import { PluginRunTable } from "@/components/PluginRunTable";
import { RunPipelineButton } from "@/components/RunPipelineButton";
import { DecisionBadge } from "@/components/validation/ValidationCard";
import { api } from "@/lib/api";
import { dateTime, titleCase } from "@/lib/format";
import type { ProductListItem } from "@/types/api";

export default function DashboardPage() {
  const opportunities = useQuery({
    queryKey: ["opportunities", { limit: 100, validation: true }],
    queryFn: () => api.opportunities({ limit: 100 })
  });
  const runs = useQuery({
    queryKey: ["plugin-runs", 8],
    queryFn: () => api.pluginRuns(8)
  });

  const products = opportunities.data?.items ?? [];
  const buckets = {
    strong: products.filter((product) => product.validation_decision === "pursue"),
    needsQuote: products.filter(
      (product) =>
        product.supplier_validation_decision === "needs_supplier_quote" ||
        product.economics_decision === "needs_supplier_quote"
    ),
    aboveCeiling: products.filter(
      (product) =>
        product.economics_decision === "quote_above_ceiling" ||
        product.supplier_validation_decision === "quote_above_ceiling"
    ),
    constraintFailures: products.filter((product) => product.constraint_eligible === false),
    watchlist: products.filter((product) => product.validation_decision === "watch"),
    recent: [...products].sort(
      (left, right) => new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime()
    )
  };

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 border-b border-terminal-line pb-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="font-mono text-xs uppercase tracking-[0.24em] text-terminal-green">
            Product Discovery Terminal
          </div>
          <h1 className="mt-2 text-2xl font-semibold">Validation command center</h1>
        </div>
        <RunPipelineButton />
      </header>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
        <Metric label="Strong" value={buckets.strong.length} tone="green" />
        <Metric label="Needs quote" value={buckets.needsQuote.length} tone="amber" />
        <Metric label="Above ceiling" value={buckets.aboveCeiling.length} tone="rose" />
        <Metric label="Constraint fails" value={buckets.constraintFailures.length} tone="rose" />
        <Metric label="Watchlist" value={buckets.watchlist.length} />
        <Metric label="Candidates" value={opportunities.data?.total ?? 0} />
      </div>

      {opportunities.isError ? (
        <div className="border border-terminal-rose/50 bg-terminal-rose/5 p-3 text-sm text-terminal-rose">
          Validation data unavailable: {opportunities.error.message}
        </div>
      ) : null}

      <section className="grid gap-x-5 gap-y-6 xl:grid-cols-2">
        <Bucket title="Strong opportunities" items={buckets.strong} icon={CheckCircle2} tone="green" empty="No products have cleared all validation gates." />
        <Bucket title="Needs supplier quote" items={buckets.needsQuote} icon={Store} tone="amber" empty="No products are waiting on a supplier quote." />
        <Bucket title="Above cost ceiling" items={buckets.aboveCeiling} icon={XCircle} tone="rose" empty="No current supplier quotes exceed the modeled ceiling." />
        <Bucket title="Constraint failures" items={buckets.constraintFailures} icon={SearchX} tone="rose" empty="No hard constraint failures." />
        <Bucket title="Watchlist" items={buckets.watchlist} icon={Clock3} tone="neutral" empty="No products are currently on watch." />
        <Bucket title="Recently discovered" items={buckets.recent} icon={ArrowRight} tone="neutral" empty="No candidates discovered yet." />
      </section>

      <section>
        <SectionTitle title="Recent plugin runs" />
        {runs.data?.length ? <PluginRunTable runs={runs.data} /> : <EmptyState label="No plugin runs recorded" />}
      </section>

      <div className="flex items-start gap-2 border border-terminal-amber/40 bg-terminal-amber/5 px-3 py-2 text-xs text-terminal-amber">
        <AlertTriangle size={14} className="mt-0.5 shrink-0" />
        <span>Dashboard decisions are validation guidance only. No automatic buy, sell, or sourcing action is executed.</span>
      </div>
    </div>
  );
}

function Bucket({
  title,
  items,
  icon: Icon,
  tone,
  empty
}: {
  title: string;
  items: ProductListItem[];
  icon: typeof CheckCircle2;
  tone: "green" | "amber" | "rose" | "neutral";
  empty: string;
}) {
  const toneClass =
    tone === "green"
      ? "text-terminal-green"
      : tone === "amber"
        ? "text-terminal-amber"
        : tone === "rose"
          ? "text-terminal-rose"
          : "text-terminal-muted";
  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="flex items-center gap-2 font-mono text-xs uppercase tracking-[0.18em] text-terminal-muted">
          <Icon size={14} className={toneClass} />
          {title}
        </h2>
        <span className="font-mono text-xs text-terminal-muted">{items.length}</span>
      </div>
      <div className="border border-terminal-line bg-terminal-bg">
        {items.length ? (
          items.slice(0, 5).map((product) => (
            <Link
              key={product.id}
              href={`/products/${product.id}`}
              className="grid grid-cols-[minmax(0,1fr)_auto] gap-3 border-b border-terminal-line/70 px-3 py-2.5 last:border-b-0 hover:bg-terminal-panel/70"
            >
              <div className="min-w-0">
                <div className="truncate text-sm font-medium">{titleCase(product.canonical_name)}</div>
                <div className="mt-1 flex flex-wrap gap-2 font-mono text-[11px] text-terminal-muted">
                  <span>{titleCase(product.category)}</span>
                  <span>Evidence {product.cross_source_confidence_score?.toFixed(0) ?? "--"}</span>
                  {product.missing_evidence.length ? (
                    <span className="text-terminal-amber">{product.missing_evidence.length} missing</span>
                  ) : null}
                </div>
              </div>
              <div className="flex flex-col items-end gap-1">
                <DecisionBadge value={product.validation_decision} />
                <span className="font-mono text-[10px] text-terminal-muted">{dateTime(product.updated_at)}</span>
              </div>
            </Link>
          ))
        ) : (
          <div className="px-3 py-4 text-sm text-terminal-muted">{empty}</div>
        )}
      </div>
    </div>
  );
}

function Metric({ label, value, tone = "neutral" }: { label: string; value: number; tone?: "neutral" | "green" | "amber" | "rose" }) {
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
