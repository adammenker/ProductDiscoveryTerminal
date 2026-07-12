"use client";

import clsx from "clsx";
import { useMutation } from "@tanstack/react-query";
import { ClipboardCheck, ExternalLink, Loader2, Play } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
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
import { api } from "@/lib/api";
import {
  useCreateRecommendationFeedback,
  useEvaluateConstraints,
  useProductDetail,
  useUpdateComparable
} from "@/lib/validation-hooks";
import type { ComparableAsin, HistoricalChange, HistoricalSignalWindow } from "@/types/api";

export default function ProductDetailPage() {
  const params = useParams<{ id: string }>();
  const product = useProductDetail(params.id);
  const evaluate = useEvaluateConstraints(params.id);
  const updateComparable = useUpdateComparable(params.id);
  const feedback = useCreateRecommendationFeedback(params.id);
  const [feedbackReasons, setFeedbackReasons] = useState<string[]>([]);
  const startValidation = useMutation({
    mutationFn: () => api.startValidation(params.id),
    onSuccess: (project) => { window.location.href = `/validations/${project.id}`; }
  });

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
  const recommendation = data.recommendation_v2;

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
            <button
              type="button"
              onClick={() => startValidation.mutate()}
              disabled={!score || startValidation.isPending}
              className="inline-flex h-9 items-center gap-2 border border-terminal-green/60 bg-terminal-green/10 px-3 text-sm text-terminal-green disabled:opacity-50"
            >
              {startValidation.isPending ? <Loader2 size={15} className="animate-spin" /> : <ClipboardCheck size={15} />}
              Start validation
            </button>
            <RecommendationBadge value={recommendation.recommendation ?? score?.recommendation} />
            <ScoreBadge value={recommendation.opportunity_score ?? score?.final_score} />
          </div>
        </div>
      </header>

      <ValidationWarnings />

      <section className="grid gap-4 lg:grid-cols-[1fr_420px]">
        <div className="border border-terminal-line bg-terminal-panel/80 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="font-mono text-xs uppercase tracking-[0.18em] text-terminal-muted">Recommendation summary</h2>
            <DecisionBadge value={recommendation.recommendation ?? decision.decision} />
          </div>
          <p className="mt-3 text-sm leading-7 text-terminal-ink">
            {score?.explanation || decision.thesis || "No recommendation has been generated."}
          </p>
          <div className="mt-4 grid gap-2 sm:grid-cols-3">
            <Metric label="Opportunity" value={formatMetric(recommendation.opportunity_score ?? score?.final_score)} />
            <Metric label="Confidence" value={formatMetric(recommendation.evidence_confidence_score)} />
            <Metric label="Readiness" value={formatMetric(recommendation.validation_readiness_score)} />
          </div>
          {recommendation.next_actions?.length ? (
            <div className="mt-4 border-t border-terminal-line pt-3">
              <SectionTitle title="Next actions" />
              <ul className="space-y-1 text-sm text-terminal-muted">
                {recommendation.next_actions.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {(recommendation.missing_evidence?.length ?? data.missing_evidence.length) ? (
            <div className="mt-3 flex flex-wrap gap-2">
              {(recommendation.missing_evidence ?? data.missing_evidence).map((item) => (
                <span key={item} className="border border-terminal-amber/40 bg-terminal-amber/5 px-2 py-1 font-mono text-xs text-terminal-amber">
                  {item}
                </span>
              ))}
            </div>
          ) : null}
        </div>
        <div className="border border-terminal-line bg-terminal-panel/80 p-4">
          <h2 className="mb-4 font-mono text-xs uppercase tracking-[0.18em] text-terminal-muted">Recommendation V2</h2>
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
            <SectionTitle title="Comparable ASIN Review" />
            {data.comparable_asins.length ? (
              <div className="overflow-x-auto border border-terminal-line bg-terminal-bg">
                <table className="w-full min-w-[1120px] text-left text-sm">
                  <thead className="bg-terminal-panel font-mono text-xs uppercase text-terminal-muted">
                    <tr>
                      <th className="border-b border-terminal-line px-3 py-2 font-medium">Use</th>
                      <th className="border-b border-terminal-line px-3 py-2 font-medium">ASIN</th>
                      <th className="border-b border-terminal-line px-3 py-2 font-medium">Title</th>
                      <th className="border-b border-terminal-line px-3 py-2 font-medium">Brand</th>
                      <th className="border-b border-terminal-line px-3 py-2 font-medium">Type</th>
                      <th className="border-b border-terminal-line px-3 py-2 font-medium">Price</th>
                      <th className="border-b border-terminal-line px-3 py-2 font-medium">Relevance</th>
                      <th className="border-b border-terminal-line px-3 py-2 font-medium">Status</th>
                      <th className="border-b border-terminal-line px-3 py-2 font-medium">Reasons</th>
                      <th className="border-b border-terminal-line px-3 py-2 font-medium">Refreshed</th>
                      <th className="border-b border-terminal-line px-3 py-2 font-medium">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.comparable_asins.map((item, index) => (
                      <tr key={item.asin ?? index} className="border-b border-terminal-line/70 last:border-b-0">
                        <td className={clsx("px-3 py-2 font-mono text-xs", isIncluded(item) ? "text-terminal-green" : "text-terminal-muted")}>
                          {isIncluded(item) ? "Included" : "--"}
                        </td>
                        <td className="px-3 py-2 font-mono text-xs">
                          {item.url ? (
                            <a href={item.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 hover:text-terminal-green">
                              {item.asin ?? "--"} <ExternalLink size={11} />
                            </a>
                          ) : item.asin ?? "--"}
                        </td>
                        <td className="max-w-[320px] truncate px-3 py-2">{item.title ?? "--"}</td>
                        <td className="px-3 py-2 text-terminal-muted">{item.brand ?? "--"}</td>
                        <td className="px-3 py-2 text-terminal-muted">{titleCase(item.product_type)}</td>
                        <td className="px-3 py-2 font-mono text-xs">{currency(item.price)}</td>
                        <td className="px-3 py-2 font-mono text-xs tabular-nums">
                          {item.relevance_score?.toFixed(0) ?? "--"}
                        </td>
                        <td className="px-3 py-2">
                          <DecisionBadge value={item.relevance_status} />
                          {item.manually_overridden ? (
                            <div className="mt-1 font-mono text-[10px] uppercase text-terminal-muted">Manual</div>
                          ) : null}
                        </td>
                        <td className="max-w-[260px] px-3 py-2 text-xs text-terminal-muted">
                          {(item.relevance_reasons ?? []).slice(0, 2).join(" / ") || "--"}
                        </td>
                        <td className="px-3 py-2 font-mono text-xs text-terminal-muted">
                          {dateTime(item.last_refreshed_at)}
                        </td>
                        <td className="px-3 py-2">
                          <div className="flex flex-wrap gap-1">
                            <ComparableAction
                              label="Include"
                              item={item}
                              status="included"
                              pending={updateComparable.isPending}
                              onClick={(asin, status) => updateComparable.mutate({ asin, input: { relevance_status: status } })}
                            />
                            <ComparableAction
                              label="Exclude"
                              item={item}
                              status="excluded_irrelevant"
                              pending={updateComparable.isPending}
                              onClick={(asin, status) => updateComparable.mutate({ asin, input: { relevance_status: status, reason: "Manual exclusion from review table" } })}
                            />
                            <ComparableAction
                              label="Reset"
                              item={item}
                              status="reset_automatic_decision"
                              pending={updateComparable.isPending}
                              onClick={(asin, status) => updateComparable.mutate({ asin, input: { relevance_status: status } })}
                            />
                          </div>
                        </td>
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
        title="Historical signals"
        source="marketplace_asin_snapshots"
        updatedAt={data.historical_summary.derived_signals.latest_observation_at}
        confidence={null}
        missing={!data.historical_summary.snapshot_count ? ["Marketplace history"] : []}
      >
        <div className="grid gap-3 xl:grid-cols-3">
          {Object.entries(data.historical_summary.derived_signals.windows ?? {}).map(([window, signal]) => (
            <HistoricalSignalCard key={window} window={window} signal={signal} />
          ))}
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
            <div className="grid gap-2 border border-terminal-line bg-terminal-bg p-3 sm:grid-cols-2 xl:grid-cols-4">
              <Metric label="Fee status" value={economics.fee_provenance?.status ? titleCase(economics.fee_provenance.status) : titleCase(economics.fee_source)} />
              <Metric label="Price source" value={economics.fee_provenance?.modeled_price_source ? titleCase(economics.fee_provenance.modeled_price_source) : "--"} />
              <Metric label="Fee confidence" value={String(economics.fee_provenance?.confidence ?? economics.fee_source_confidence ?? "--")} />
              <Metric label="Fee ASIN" value={economics.fee_provenance?.comparable_asin ?? economics.comparable_asin ?? "--"} />
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

      <ValidationCard
        title="Analyst feedback"
        source="recommendation_feedback"
        updatedAt={score?.created_at}
        confidence={null}
        missing={[]}
      >
        <div className="mb-3 flex flex-wrap gap-2">
          {FEEDBACK_REASON_OPTIONS.map((option) => {
            const selected = feedbackReasons.includes(option.value);
            return (
              <button
                key={option.value}
                type="button"
                onClick={() => {
                  setFeedbackReasons((current) =>
                    selected
                      ? current.filter((reason) => reason !== option.value)
                      : [...current, option.value]
                  );
                }}
                className={clsx(
                  "inline-flex h-8 items-center border px-2.5 font-mono text-[11px] uppercase",
                  selected
                    ? "border-terminal-green bg-terminal-green/10 text-terminal-green"
                    : "border-terminal-line bg-terminal-bg text-terminal-muted hover:border-terminal-green hover:text-terminal-green"
                )}
              >
                {option.label}
              </button>
            );
          })}
        </div>
        <div className="flex flex-wrap gap-2">
          {[
            ["Good", "good_recommendation"],
            ["Bad", "bad_recommendation"],
            ["Uncertain", "uncertain"]
          ].map(([label, verdict]) => (
            <button
              key={verdict}
              type="button"
              disabled={feedback.isPending || feedbackReasons.length === 0}
              onClick={() => feedback.mutate({ verdict: verdict as "good_recommendation" | "bad_recommendation" | "uncertain", reasons: feedbackReasons })}
              className="inline-flex h-9 items-center border border-terminal-line bg-terminal-bg px-3 font-mono text-xs uppercase text-terminal-muted hover:border-terminal-green hover:text-terminal-green disabled:opacity-50"
            >
              {label}
            </button>
          ))}
        </div>
        {feedback.isSuccess ? <div className="mt-2 text-xs text-terminal-green">Feedback recorded.</div> : null}
        {feedback.error ? <div className="mt-2 text-xs text-terminal-rose">{feedback.error.message}</div> : null}
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

const FEEDBACK_REASON_OPTIONS = [
  { label: "Wrong comparables", value: "wrong_comparables" },
  { label: "Demand overstated", value: "demand_overstated" },
  { label: "Demand understated", value: "demand_understated" },
  { label: "Competition overstated", value: "competition_overstated" },
  { label: "Competition understated", value: "competition_understated" },
  { label: "Bad price", value: "bad_price_estimate" },
  { label: "Bad fee", value: "bad_fee_estimate" },
  { label: "Missing risk", value: "missing_risk" },
  { label: "Missing data", value: "missing_data_mishandled" },
  { label: "Interesting", value: "actually_interesting" },
  { label: "Unattractive", value: "actually_unattractive" },
  { label: "Other", value: "other" }
] as const;

function HistoricalSignalCard({
  window,
  signal
}: {
  window: string;
  signal: HistoricalSignalWindow;
}) {
  const cohortPrice = signal.cohort_change?.price;
  const matchedPrice = signal.matched_asin_change?.price;
  const matchedCount = signal.matched_asin_change?.matched_asin_count;
  const churn = signal.comparable_churn;

  return (
    <div className="border border-terminal-line bg-terminal-bg p-3">
      <div className="flex items-center justify-between gap-2">
        <div className="font-mono text-xs uppercase text-terminal-muted">{window}</div>
        <DecisionBadge value={signal.status ?? "missing"} />
      </div>
      <div className="mt-3 grid gap-2 text-xs text-terminal-muted">
        <div className="grid grid-cols-2 gap-2">
          <Metric label="Cohorts" value={String(signal.cohort_count ?? 0)} />
          <Metric label="Confidence" value={formatMetric(signal.confidence)} />
        </div>
        <HistoryLine label="Whole-cohort price" value={historicalChange(cohortPrice)} />
        <HistoryLine label="Matched-ASIN price" value={historicalChange(isChange(matchedPrice) ? matchedPrice : undefined)} />
        <HistoryLine label="Matched ASINs" value={String(typeof matchedCount === "number" ? matchedCount : 0)} />
        <HistoryLine label="Comparable churn" value={churn?.churn_percent != null ? `${churn.churn_percent.toFixed(1)}%` : "--"} />
      </div>
    </div>
  );
}

function HistoryLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 border-t border-terminal-line/70 pt-2">
      <span>{label}</span>
      <span className="font-mono text-terminal-ink">{value}</span>
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

function ComparableAction({
  label,
  item,
  status,
  pending,
  onClick
}: {
  label: string;
  item: ComparableAsin;
  status: string;
  pending: boolean;
  onClick: (asin: string, status: string) => void;
}) {
  return (
    <button
      type="button"
      disabled={pending || !item.asin}
      onClick={() => onClick(item.asin, status)}
      className="inline-flex h-7 items-center border border-terminal-line px-2 font-mono text-[10px] uppercase text-terminal-muted hover:border-terminal-green hover:text-terminal-green disabled:opacity-50"
    >
      {label}
    </button>
  );
}

function isIncluded(item: ComparableAsin) {
  return item.relevance_status === "included" || item.relevance_status === "manually_included";
}

function formatMetric(value?: number | null) {
  return value == null ? "--" : value.toFixed(0);
}

function isChange(value: unknown): value is HistoricalChange {
  return Boolean(value && typeof value === "object" && "absolute_change" in value);
}

function historicalChange(value?: HistoricalChange) {
  if (!value || value.absolute_change == null) return "--";
  const percentText = value.percent_change == null ? "" : ` / ${value.percent_change.toFixed(1)}%`;
  return `${value.absolute_change.toFixed(1)}${percentText}`;
}
