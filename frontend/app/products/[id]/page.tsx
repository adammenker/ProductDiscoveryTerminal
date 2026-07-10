"use client";

import clsx from "clsx";
import { ExternalLink, Loader2, Play } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { EmptyState } from "@/components/EmptyState";
import { RecommendationBadge } from "@/components/RecommendationBadge";
import { RecordTable } from "@/components/RecordTable";
import { ScoreBadge } from "@/components/ScoreBadge";
import { ScoreBreakdown } from "@/components/ScoreBreakdown";
import { SnapshotControl } from "@/components/validation/SnapshotControl";
import { SupplierQuoteForm } from "@/components/validation/SupplierQuoteForm";
import {
  DecisionBadge,
  EvidenceMatrixTable,
  ValidationCard,
  ValidationWarnings,
  WarningList
} from "@/components/validation/ValidationCard";
import { currency, dateTime, percent, titleCase } from "@/lib/format";
import { useEvaluateConstraints, useProductDetail } from "@/lib/validation-hooks";

export default function ProductDetailPage() {
  const params = useParams<{ id: string }>();
  const product = useProductDetail(params.id);
  const evaluate = useEvaluateConstraints(params.id);

  if (product.isLoading) return <EmptyState label="Loading product detail" />;
  if (product.isError) return <EmptyState label={`Product detail unavailable: ${product.error.message}`} />;
  if (!product.data) return <EmptyState label="Product not found" />;

  const data = product.data;
  const score = data.latest_score;
  const economics = data.economics_validator;
  const modeled = economics.modeled;
  const supplier = data.supplier_validation;
  const constraints = data.constraint_evaluation;
  const decision = data.validation_decision;

  return (
    <div className="space-y-6">
      <header className="border-b border-terminal-line pb-5">
        <Link href="/products" className="font-mono text-xs uppercase tracking-[0.18em] text-terminal-muted hover:text-terminal-green">
          Products
        </Link>
        <div className="mt-3 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h1 className="text-2xl font-semibold">{titleCase(data.product.canonical_name)}</h1>
            <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-terminal-muted">
              <span>{titleCase(data.product.category)}</span>
              <span>/</span>
              <span>{titleCase(data.product.status)}</span>
              <span>/</span>
              <span>{dateTime(data.product.updated_at)}</span>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <DecisionBadge value={decision.decision} />
            <RecommendationBadge value={score?.recommendation} />
            <ScoreBadge value={score?.final_score} />
          </div>
        </div>
      </header>

      <ValidationWarnings />

      <section className="grid gap-4 lg:grid-cols-[1fr_360px]">
        <div className="border border-terminal-line bg-terminal-panel/80 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="font-mono text-xs uppercase tracking-[0.18em] text-terminal-muted">Opportunity thesis</h2>
            <span className="font-mono text-xs text-terminal-muted">
              {data.cross_source_confidence_score}/100 cross-source confidence
            </span>
          </div>
          <p className="mt-3 text-sm leading-7 text-terminal-ink">
            {decision.thesis || score?.explanation || "No opportunity thesis has been generated."}
          </p>
          {data.missing_evidence.length ? (
            <div className="mt-3 flex flex-wrap gap-2">
              {data.missing_evidence.map((item) => (
                <span key={item} className="border border-terminal-amber/40 bg-terminal-amber/5 px-2 py-1 font-mono text-xs text-terminal-amber">
                  {item}
                </span>
              ))}
            </div>
          ) : null}
        </div>
        <div className="border border-terminal-line bg-terminal-panel/80 p-4">
          <h2 className="mb-4 font-mono text-xs uppercase tracking-[0.18em] text-terminal-muted">Discovery score</h2>
          {score ? <ScoreBreakdown score={score} /> : <EmptyState label="No discovery score" />}
        </div>
      </section>

      <ValidationCard
        title="Discovery source"
        source={data.discovery_source.primary}
        updatedAt={data.discovery_source.last_updated}
        confidence={data.discovery_source.confidence}
        missing={!data.discovery_source.sources.length ? ["Source provenance"] : []}
      >
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {data.discovery_source.sources.length ? data.discovery_source.sources.map((source) => (
              <span key={source} className="border border-terminal-line bg-terminal-bg px-2 py-1 font-mono text-xs text-terminal-muted">
                {titleCase(source)}
              </span>
            )) : <span className="text-sm text-terminal-muted">Manual candidate; no source observations are linked.</span>}
          </div>

          <div>
            <SectionTitle title="Comparable ASINs" />
            {data.comparable_asins.length ? (
              <div className="overflow-x-auto border border-terminal-line bg-terminal-bg">
                <table className="w-full min-w-[720px] text-left text-sm">
                  <thead className="bg-terminal-panel font-mono text-xs uppercase text-terminal-muted">
                    <tr>
                      <th className="border-b border-terminal-line px-3 py-2 font-medium">ASIN</th>
                      <th className="border-b border-terminal-line px-3 py-2 font-medium">Title</th>
                      <th className="border-b border-terminal-line px-3 py-2 font-medium">Brand</th>
                      <th className="border-b border-terminal-line px-3 py-2 font-medium">Price</th>
                      <th className="border-b border-terminal-line px-3 py-2 font-medium">Proxy</th>
                      <th className="border-b border-terminal-line px-3 py-2 font-medium">Source</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.comparable_asins.map((item, index) => (
                      <tr key={item.asin ?? index} className="border-b border-terminal-line/70 last:border-b-0">
                        <td className="px-3 py-2 font-mono text-xs">
                          {item.url ? (
                            <a href={item.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 hover:text-terminal-green">
                              {item.asin ?? "--"} <ExternalLink size={11} />
                            </a>
                          ) : item.asin ?? "--"}
                        </td>
                        <td className="max-w-[320px] truncate px-3 py-2">{item.title ?? "--"}</td>
                        <td className="px-3 py-2 text-terminal-muted">{item.brand ?? "--"}</td>
                        <td className="px-3 py-2 font-mono text-xs">{currency(item.price)}</td>
                        <td className={clsx("px-3 py-2 font-mono text-xs", item.selected_proxy ? "text-terminal-green" : "text-terminal-muted")}>
                          {item.selected_proxy ? "Selected" : "--"}
                        </td>
                        <td className="px-3 py-2 text-terminal-muted">{titleCase(item.source)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState label="No Amazon comparable evidence linked" />
            )}
          </div>
        </div>
      </ValidationCard>

      <ValidationCard
        title="Economics validator"
        source={economics.fee_source}
        updatedAt={economics.updated_at}
        confidence={economics.fee_source_confidence}
        missing={!modeled ? ["Selling price or Amazon fee evidence"] : []}
      >
        {modeled ? (
          <div className="space-y-4">
            <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-6">
              <Metric label="Modeled price" value={currency(modeled.selling_price)} />
              <Metric label="Amazon fees" value={currency(modeled.amazon_fees)} />
              <Metric label="Max landed" value={currency(modeled.max_landed_cost)} tone="green" />
              <Metric label="Supplier landed" value={currency(modeled.supplier_landed_cost)} />
              <Metric label="Safety" value={currency(modeled.margin_of_safety)} tone={(modeled.margin_of_safety ?? 0) < 0 ? "rose" : "green"} />
              <Metric label="Profit margin" value={percent(modeled.estimated_profit_margin_after_allowances)} />
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <DecisionBadge value={economics.decision} />
              <span className="font-mono text-xs text-terminal-muted">
                {modeled.target_margin_percent}% target margin / fee source {titleCase(economics.fee_source)}
              </span>
            </div>
            <WarningList warnings={economics.warnings} />
          </div>
        ) : (
          <EmptyState label="Economics cannot be modeled from current evidence" />
        )}
      </ValidationCard>

      <ValidationCard
        title="Supplier validation"
        source={supplier.source}
        updatedAt={supplier.updated_at}
        confidence={supplier.supplier_validation_score}
        missing={!supplier.quotes.length ? ["Supplier quote"] : []}
      >
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <DecisionBadge value={supplier.decision} />
            <span className="font-mono text-xs text-terminal-muted">
              {supplier.viable_quote_count} viable / {supplier.quotes.length} total / ceiling {currency(supplier.max_landed_cost)}
            </span>
          </div>
          {supplier.quotes.length ? (
            <RecordTable
              rows={supplier.quotes}
              columns={["supplier_name", "supplier_landed_cost", "max_landed_cost", "margin_of_safety", "moq", "lead_time_days", "decision", "quote_status"]}
            />
          ) : null}
          <details className="border-t border-terminal-line pt-3">
            <summary className="cursor-pointer font-mono text-xs uppercase text-terminal-muted hover:text-terminal-ink">Add supplier quote</summary>
            <div className="mt-3">
              <SupplierQuoteForm productId={params.id} />
            </div>
          </details>
        </div>
      </ValidationCard>

      <ValidationCard
        title="Constraint fit"
        source={constraints.rule_profile_name}
        updatedAt={constraints.created_at}
        confidence={constraints.constraint_score}
        missing={!constraints.rule_profile_id ? ["Rule profile evaluation"] : []}
        action={
          <button
            type="button"
            onClick={() => evaluate.mutate()}
            disabled={evaluate.isPending}
            className="inline-flex h-8 items-center gap-2 border border-terminal-green/60 bg-terminal-green/10 px-2.5 text-xs text-terminal-green disabled:opacity-50"
          >
            {evaluate.isPending ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
            Re-evaluate
          </button>
        }
      >
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <DecisionBadge value={constraints.eligible ? "pursue" : "skip"} />
            <span className="text-sm">{constraints.explanation}</span>
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <MessageList title="Hard failures" rows={constraints.hard_failures} tone="rose" empty="No hard failures." />
            <MessageList title="Soft warnings" rows={constraints.soft_warnings} tone="amber" empty="No soft warnings." />
          </div>
          {evaluate.error ? <div className="text-xs text-terminal-rose">{evaluate.error.message}</div> : null}
        </div>
      </ValidationCard>

      <ValidationCard
        title="Evidence matrix"
        source={data.discovery_source.sources.join(", ")}
        updatedAt={data.product.updated_at}
        confidence={data.cross_source_confidence_score}
        missing={data.missing_evidence}
      >
        <EvidenceMatrixTable rows={data.evidence_matrix} />
      </ValidationCard>

      <ValidationCard
        title="Paper trading history"
        source="paper_trades"
        updatedAt={data.paper_trading_history[0]?.created_at}
        confidence={null}
        missing={!data.paper_trading_history.length ? ["Paper-trade history"] : []}
      >
        <div className="space-y-4">
          <SnapshotControl productId={params.id} />
          {data.paper_trading_history.length ? (
            <div className="overflow-x-auto border border-terminal-line bg-terminal-bg">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead className="bg-terminal-panel font-mono text-xs uppercase text-terminal-muted">
                  <tr>
                    <th className="border-b border-terminal-line px-3 py-2 font-medium">Entry</th>
                    <th className="border-b border-terminal-line px-3 py-2 font-medium">Decision</th>
                    <th className="border-b border-terminal-line px-3 py-2 font-medium">Hypothesis</th>
                    <th className="border-b border-terminal-line px-3 py-2 font-medium">Windows</th>
                    <th className="border-b border-terminal-line px-3 py-2 font-medium">Outcomes</th>
                    <th className="border-b border-terminal-line px-3 py-2 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {data.paper_trading_history.map((trade) => (
                    <tr key={trade.id} className="border-b border-terminal-line/70 last:border-b-0">
                      <td className="px-3 py-2 font-mono text-xs text-terminal-muted">{dateTime(trade.entry_date)}</td>
                      <td className="px-3 py-2"><DecisionBadge value={trade.decision} /></td>
                      <td className="max-w-[360px] truncate px-3 py-2 text-terminal-muted">{trade.hypothesis ?? "--"}</td>
                      <td className="px-3 py-2 font-mono text-xs">{trade.evaluation_windows.join("/")}</td>
                      <td className="px-3 py-2 font-mono text-xs">{trade.outcomes.length}</td>
                      <td className="px-3 py-2 font-mono text-xs uppercase text-terminal-muted">{trade.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </div>
      </ValidationCard>

      <section>
        <SectionTitle title="Raw data views" />
        <div className="border border-terminal-line bg-terminal-panel/50">
          <RawSection title="Signals">
            <div className="grid gap-4 xl:grid-cols-2">
              <RecordTable rows={data.market_signals} columns={["source", "signal_type", "value", "unit", "created_at"]} />
              <RecordTable rows={data.supplier_signals} columns={["source", "supplier_name", "unit_cost", "moq", "lead_time_days", "shipping_estimate"]} />
            </div>
          </RawSection>
          <RawSection title="Cost models">
            <RecordTable rows={data.cost_models} columns={["model_name", "selling_price", "unit_cost", "freight_cost_per_unit", "fulfillment_cost_per_unit", "marketplace_fee_per_unit", "storage_cost_per_unit", "estimated_net_margin"]} />
          </RawSection>
          <RawSection title="Insights">
            <RecordTable rows={data.insights} columns={["insight_type", "title", "body", "confidence", "created_at"]} />
          </RawSection>
          <RawSection title="Observations">
            <RecordTable rows={data.recent_observations} columns={["source", "entity_type", "external_id", "title", "url", "raw_text", "created_at"]} />
          </RawSection>
        </div>
      </section>
    </div>
  );
}

function MessageList({
  title,
  rows,
  tone,
  empty
}: {
  title: string;
  rows: Array<{ rule: string; message: string }>;
  tone: "rose" | "amber";
  empty: string;
}) {
  return (
    <div>
      <SectionTitle title={title} />
      <div className="border border-terminal-line bg-terminal-bg">
        {rows.length ? rows.map((row) => (
          <div key={`${row.rule}-${row.message}`} className={clsx("border-b border-terminal-line/70 px-3 py-2 text-sm last:border-b-0", tone === "rose" ? "text-terminal-rose" : "text-terminal-amber")}>
            {row.message}
          </div>
        )) : <div className="px-3 py-2 text-sm text-terminal-muted">{empty}</div>}
      </div>
    </div>
  );
}

function RawSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <details className="border-b border-terminal-line last:border-b-0">
      <summary className="cursor-pointer px-4 py-3 font-mono text-xs uppercase text-terminal-muted hover:bg-terminal-panel hover:text-terminal-ink">
        {title}
      </summary>
      <div className="border-t border-terminal-line p-4">{children}</div>
    </details>
  );
}

function Metric({
  label,
  value,
  tone = "neutral"
}: {
  label: string;
  value: string;
  tone?: "neutral" | "green" | "rose";
}) {
  const toneClass =
    tone === "green" ? "text-terminal-green" : tone === "rose" ? "text-terminal-rose" : "text-terminal-ink";
  return (
    <div className="border-l-2 border-terminal-line bg-terminal-bg px-3 py-2">
      <div className="font-mono text-[11px] uppercase text-terminal-muted">{label}</div>
      <div className={`mt-1 font-mono text-base tabular-nums ${toneClass}`}>{value}</div>
    </div>
  );
}

function SectionTitle({ title }: { title: string }) {
  return <h3 className="mb-3 font-mono text-xs uppercase tracking-[0.18em] text-terminal-muted">{title}</h3>;
}
