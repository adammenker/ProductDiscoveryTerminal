"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { EmptyState } from "@/components/EmptyState";
import { RecommendationBadge } from "@/components/RecommendationBadge";
import { RecordTable } from "@/components/RecordTable";
import { ScoreBadge } from "@/components/ScoreBadge";
import { ScoreBreakdown } from "@/components/ScoreBreakdown";
import { api } from "@/lib/api";
import { dateTime, titleCase } from "@/lib/format";

export default function ProductDetailPage() {
  const params = useParams<{ id: string }>();
  const product = useQuery({
    queryKey: ["product", params.id],
    queryFn: () => api.product(params.id),
    enabled: Boolean(params.id)
  });

  if (product.isLoading) return <EmptyState label="Loading product detail" />;
  if (!product.data) return <EmptyState label="Product not found" />;

  const data = product.data;
  const score = data.latest_score;

  return (
    <div className="space-y-6">
      <div className="border-b border-terminal-line pb-5">
        <Link href="/products" className="font-mono text-xs uppercase tracking-[0.18em] text-terminal-muted hover:text-terminal-green">
          Products
        </Link>
        <div className="mt-3 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h1 className="text-2xl font-semibold">{titleCase(data.product.canonical_name)}</h1>
            <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-terminal-muted">
              <span>{titleCase(data.product.category)}</span>
              <span>/</span>
              <span>{dateTime(data.product.updated_at)}</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <RecommendationBadge value={score?.recommendation} />
            <ScoreBadge value={score?.final_score} />
          </div>
        </div>
      </div>

      {score ? (
        <section className="grid gap-5 lg:grid-cols-[1fr_420px]">
          <div className="border border-terminal-line bg-terminal-panel/80 p-4">
            <h2 className="font-mono text-xs uppercase tracking-[0.18em] text-terminal-muted">Opportunity Thesis</h2>
            <p className="mt-3 leading-7 text-terminal-ink">{score.explanation}</p>
          </div>
          <div className="border border-terminal-line bg-terminal-panel/80 p-4">
            <h2 className="mb-4 font-mono text-xs uppercase tracking-[0.18em] text-terminal-muted">Score Breakdown</h2>
            <ScoreBreakdown score={score} />
          </div>
        </section>
      ) : (
        <EmptyState label="No score has been generated for this product" />
      )}

      <section className="space-y-3">
        <SectionTitle title="Signals" />
        <div className="grid gap-4 xl:grid-cols-2">
          <RecordTable rows={data.market_signals} columns={["source", "signal_type", "value", "unit", "created_at"]} />
          <RecordTable
            rows={data.supplier_signals}
            columns={["source", "supplier_name", "unit_cost", "moq", "lead_time_days", "shipping_estimate"]}
          />
        </div>
      </section>

      <section className="space-y-3">
        <SectionTitle title="Cost Models" />
        {data.cost_models.length ? (
          <RecordTable
            rows={data.cost_models}
            columns={[
              "model_name",
              "selling_price",
              "unit_cost",
              "fulfillment_cost_per_unit",
              "marketplace_fee_per_unit",
              "estimated_net_margin"
            ]}
          />
        ) : (
          <EmptyState label="No cost model available" />
        )}
      </section>

      <section className="space-y-3">
        <SectionTitle title="Insights" />
        {data.insights.length ? (
          <div className="border border-terminal-line bg-terminal-bg">
            {data.insights.map((insight) => (
              <div key={String(insight.id)} className="border-b border-terminal-line p-4 last:border-b-0">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <h3 className="font-medium">{String(insight.title)}</h3>
                  <span className="font-mono text-xs uppercase text-terminal-muted">
                    {String(insight.insight_type).replace(/_/g, " ")}
                  </span>
                </div>
                <p className="mt-2 leading-6 text-terminal-muted">{String(insight.body)}</p>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState label="No insights available" />
        )}
      </section>

      <section className="space-y-3">
        <SectionTitle title="Evidence" />
        {data.recent_observations.length ? (
          <RecordTable
            rows={data.recent_observations}
            columns={["source", "entity_type", "title", "url", "raw_text", "created_at"]}
          />
        ) : (
          <EmptyState label="No raw observations linked" />
        )}
      </section>
    </div>
  );
}

function SectionTitle({ title }: { title: string }) {
  return <h2 className="font-mono text-xs uppercase tracking-[0.18em] text-terminal-muted">{title}</h2>;
}

