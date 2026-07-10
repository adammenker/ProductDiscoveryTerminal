"use client";

import { useQuery } from "@tanstack/react-query";
import clsx from "clsx";
import {
  AlertTriangle,
  Check,
  ChevronRight,
  Loader2,
  Play,
  Plus,
  RefreshCw,
  Search
} from "lucide-react";
import { useEffect, useState } from "react";
import { EmptyState } from "@/components/EmptyState";
import { SnapshotControl } from "@/components/validation/SnapshotControl";
import { SupplierQuoteForm } from "@/components/validation/SupplierQuoteForm";
import {
  DecisionBadge,
  EvidenceMatrixTable,
  ValidationCard,
  ValidationWarnings,
  WarningList
} from "@/components/validation/ValidationCard";
import { api } from "@/lib/api";
import { currency, titleCase } from "@/lib/format";
import {
  useCreateProduct,
  useEvaluateConstraints,
  useProductDetail,
  useRunResearch,
  useSupplierQuotes,
  useValidateProduct
} from "@/lib/validation-hooks";
import type {
  ConstraintEvaluation,
  CostScenario,
  EconomicsValidator,
  SupplierQuote,
  SupplierValidation
} from "@/types/api";

const inputClass =
  "h-9 w-full border border-terminal-line bg-terminal-bg px-2.5 text-sm outline-none placeholder:text-terminal-muted focus:border-terminal-green";

const stages = [
  ["candidate", "Candidate"],
  ["comparables", "Comparable ASINs"],
  ["economics", "Economics"],
  ["supplier", "Supplier quote"],
  ["constraints", "Constraints"],
  ["decision", "Evidence + decision"]
] as const;

export default function ValidatorPage() {
  const [selectedProductId, setSelectedProductId] = useState("");
  const [targetMargin, setTargetMargin] = useState(30);
  const [selectedAsins, setSelectedAsins] = useState<string[]>([]);
  const products = useQuery({
    queryKey: ["products", "validator"],
    queryFn: () => api.products({ limit: 200 })
  });
  const detail = useProductDetail(selectedProductId);
  const validation = useValidateProduct(selectedProductId);
  const quotes = useSupplierQuotes(selectedProductId);
  const constraints = useEvaluateConstraints(selectedProductId);
  const research = useRunResearch(selectedProductId);

  useEffect(() => {
    setSelectedAsins(
      (detail.data?.comparable_asins ?? [])
        .filter((item) => item.selected_proxy && item.asin)
        .map((item) => item.asin as string)
    );
  }, [detail.data?.comparable_asins]);

  const economics = validation.data?.economics_validator;
  const modeled =
    economics?.scenarios.find((scenario) => scenario.target_margin_percent === targetMargin) ??
    economics?.modeled ??
    null;
  const selectedProduct = detail.data?.product;

  function runResearch(plugins?: string[]) {
    if (!selectedProduct) return;
    research.mutate({
      plugins,
      query: {
        query: selectedProduct.canonical_name,
        category: selectedProduct.category,
        limit: 50,
        metadata: {
          product_id: selectedProduct.id,
          comparable_asins: selectedAsins
        }
      },
      run_analyzers: true,
      score: true
    });
  }

  return (
    <div className="space-y-5">
      <header className="border-b border-terminal-line pb-5">
        <div className="font-mono text-xs uppercase tracking-[0.24em] text-terminal-green">Discovery validator</div>
        <div className="mt-2 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h1 className="text-2xl font-semibold">Validation workflow</h1>
            <p className="mt-1 text-sm text-terminal-muted">
              {selectedProduct ? titleCase(selectedProduct.canonical_name) : "Select or create a candidate to begin."}
            </p>
          </div>
          {validation.data ? (
            <div className="flex items-center gap-3">
              <span className="font-mono text-sm text-terminal-muted">
                {validation.data.validation_decision.cross_source_confidence_score}/100 evidence
              </span>
              <DecisionBadge value={validation.data.validation_decision.decision} />
            </div>
          ) : null}
        </div>
      </header>

      <ValidationWarnings />

      <div className="grid gap-5 xl:grid-cols-[190px_minmax(0,1fr)]">
        <nav className="h-fit border border-terminal-line bg-terminal-panel/80 p-2 xl:sticky xl:top-6">
          {stages.map(([id, label], index) => (
            <a
              key={id}
              href={`#${id}`}
              className="flex h-10 items-center gap-2 border-b border-terminal-line/60 px-2 text-sm text-terminal-muted last:border-b-0 hover:bg-terminal-bg hover:text-terminal-ink"
            >
              <span className="flex h-5 w-5 items-center justify-center border border-terminal-line font-mono text-[10px]">
                {index + 1}
              </span>
              <span className="min-w-0 truncate">{label}</span>
              <ChevronRight size={13} className="ml-auto" />
            </a>
          ))}
        </nav>

        <div className="min-w-0 space-y-5">
          <div id="candidate">
            <CandidateStage
              products={products.data?.items ?? []}
              selectedProductId={selectedProductId}
              onSelect={setSelectedProductId}
              onRunDiscovery={() => runResearch()}
              discoveryPending={research.isPending}
              discoveryResult={research.data?.status}
              discoveryError={research.error?.message}
              source={detail.data?.discovery_source}
            />
          </div>

          <div id="comparables">
            <ValidationCard
              title="02 / Comparable ASINs"
              source={detail.data?.discovery_source.sources.find((source) => source.toLowerCase().includes("amazon"))}
              updatedAt={detail.data?.discovery_source.last_updated}
              confidence={economics?.fee_source_confidence}
              missing={!detail.data?.comparable_asins.length ? ["Amazon comparable-ASIN research"] : []}
              action={
                <button
                  type="button"
                  onClick={() => runResearch(["amazon_catalog_spapi", "amazon_pricing_spapi", "amazon_fees_spapi"])}
                  disabled={!selectedProductId || research.isPending}
                  className="inline-flex h-8 items-center gap-2 border border-terminal-cyan/60 bg-terminal-cyan/10 px-2.5 text-xs text-terminal-cyan disabled:opacity-40"
                >
                  {research.isPending ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />}
                  Run Amazon research
                </button>
              }
            >
              {detail.data?.comparable_asins.length ? (
                <div className="space-y-3">
                  <div className="overflow-x-auto border border-terminal-line bg-terminal-bg">
                    <table className="w-full min-w-[760px] border-collapse text-left text-sm">
                      <thead className="bg-terminal-panel font-mono text-xs uppercase text-terminal-muted">
                        <tr>
                          <th className="border-b border-terminal-line px-3 py-2 font-medium">Proxy</th>
                          <th className="border-b border-terminal-line px-3 py-2 font-medium">ASIN</th>
                          <th className="border-b border-terminal-line px-3 py-2 font-medium">Title</th>
                          <th className="border-b border-terminal-line px-3 py-2 font-medium">Brand</th>
                          <th className="border-b border-terminal-line px-3 py-2 font-medium">Price</th>
                          <th className="border-b border-terminal-line px-3 py-2 font-medium">Fees</th>
                          <th className="border-b border-terminal-line px-3 py-2 font-medium">Reviews</th>
                        </tr>
                      </thead>
                      <tbody>
                        {detail.data.comparable_asins.map((item, index) => {
                          const asin = item.asin ?? `row-${index}`;
                          const selected = item.asin ? selectedAsins.includes(item.asin) : false;
                          return (
                            <tr key={asin} className="border-b border-terminal-line/70 last:border-b-0">
                              <td className="px-3 py-2">
                                <button
                                  type="button"
                                  disabled={!item.asin}
                                  onClick={() =>
                                    item.asin &&
                                    setSelectedAsins((current) =>
                                      current.includes(item.asin as string)
                                        ? current.filter((value) => value !== item.asin)
                                        : [...current, item.asin as string]
                                    )
                                  }
                                  title={selected ? "Deselect proxy" : "Select proxy"}
                                  className={clsx(
                                    "flex h-6 w-6 items-center justify-center border",
                                    selected
                                      ? "border-terminal-green bg-terminal-green/10 text-terminal-green"
                                      : "border-terminal-line text-terminal-muted"
                                  )}
                                >
                                  {selected ? <Check size={13} /> : null}
                                </button>
                              </td>
                              <td className="px-3 py-2 font-mono text-xs">{item.asin ?? "--"}</td>
                              <td className="max-w-[300px] truncate px-3 py-2">{item.title ?? "--"}</td>
                              <td className="px-3 py-2 text-terminal-muted">{item.brand ?? "--"}</td>
                              <td className="px-3 py-2 font-mono text-xs">{currency(item.price)}</td>
                              <td className="px-3 py-2 font-mono text-xs">{currency(item.fees)}</td>
                              <td className="px-3 py-2 font-mono text-xs">{item.review_count ?? "--"}</td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <ActionButton icon={RefreshCw} label="Refresh pricing" onClick={() => runResearch(["amazon_pricing_spapi"])} pending={research.isPending} />
                    <ActionButton icon={Play} label="Estimate fees" onClick={() => runResearch(["amazon_fees_spapi"])} pending={research.isPending} />
                    <span className="font-mono text-xs text-terminal-muted">{selectedAsins.length} session proxy selection(s)</span>
                  </div>
                </div>
              ) : (
                <EmptyState label={selectedProductId ? "No comparable ASIN evidence yet" : "Select a product to load comparables"} />
              )}
            </ValidationCard>
          </div>

          <div id="economics">
            <EconomicsStage economics={economics} modeled={modeled} targetMargin={targetMargin} setTargetMargin={setTargetMargin} />
          </div>

          <div id="supplier">
            <SupplierStage
              productId={selectedProductId}
              quotes={quotes.data ?? validation.data?.supplier_validation.quotes ?? []}
              validation={validation.data?.supplier_validation}
            />
          </div>

          <div id="constraints">
            <ConstraintStage
              productId={selectedProductId}
              evaluation={validation.data?.constraint_evaluation}
              pending={constraints.isPending}
              error={constraints.error?.message}
              onEvaluate={() => constraints.mutate()}
            />
          </div>

          <div id="decision">
            <ValidationCard
              title="06 / Evidence matrix + decision"
              source={validation.data?.evidence_matrix.sources.join(", ")}
              updatedAt={validation.data?.evidence_matrix.updated_at}
              confidence={validation.data?.evidence_matrix.cross_source_confidence_score}
              missing={validation.data?.validation_decision.missing_evidence ?? ["Validation evidence"]}
            >
              {validation.data ? (
                <div className="space-y-4">
                  <div className="flex flex-col gap-3 border-b border-terminal-line pb-4 lg:flex-row lg:items-start lg:justify-between">
                    <p className="max-w-3xl text-sm leading-6 text-terminal-ink">
                      {validation.data.validation_decision.thesis}
                    </p>
                    <DecisionBadge value={validation.data.validation_decision.decision} />
                  </div>
                  <EvidenceMatrixTable rows={validation.data.evidence_matrix.rows} />
                  <div className="border-t border-terminal-line pt-4">
                    <h3 className="mb-3 font-mono text-xs uppercase text-terminal-muted">Paper snapshot</h3>
                    <SnapshotControl productId={selectedProductId} />
                  </div>
                </div>
              ) : (
                <EmptyState label={selectedProductId ? "Validation decision unavailable" : "Select a product to build evidence"} />
              )}
            </ValidationCard>
          </div>
        </div>
      </div>
    </div>
  );
}

function CandidateStage({
  products,
  selectedProductId,
  onSelect,
  onRunDiscovery,
  discoveryPending,
  discoveryResult,
  discoveryError,
  source
}: {
  products: Array<{ id: string; canonical_name: string; category: string | null }>;
  selectedProductId: string;
  onSelect: (id: string) => void;
  onRunDiscovery: () => void;
  discoveryPending: boolean;
  discoveryResult?: string;
  discoveryError?: string;
  source?: { primary: string; sources: string[]; last_updated: string | null; confidence: number | null };
}) {
  const createProduct = useCreateProduct();
  const [form, setForm] = useState({
    canonical_name: "",
    category: "",
    candidate_source: "manual",
    notes: "",
    target_margin: "30"
  });

  return (
    <ValidationCard
      title="01 / Product candidate + discovery source"
      source={source?.primary}
      updatedAt={source?.last_updated}
      confidence={source?.confidence}
      missing={!selectedProductId ? ["Product candidate"] : source?.sources.length ? [] : ["Discovery source evidence"]}
    >
      <div className="grid gap-5 lg:grid-cols-2">
        <div>
          <h3 className="mb-3 font-mono text-xs uppercase text-terminal-muted">Find existing product</h3>
          <select value={selectedProductId} onChange={(event) => onSelect(event.target.value)} className={inputClass}>
            <option value="">Select candidate</option>
            {products.map((product) => (
              <option key={product.id} value={product.id}>
                {titleCase(product.canonical_name)}{product.category ? ` / ${titleCase(product.category)}` : ""}
              </option>
            ))}
          </select>
          {selectedProductId ? (
            <button
              type="button"
              onClick={onRunDiscovery}
              disabled={discoveryPending}
              className="mt-3 inline-flex h-9 items-center gap-2 border border-terminal-cyan/60 bg-terminal-cyan/10 px-3 text-sm text-terminal-cyan disabled:opacity-50"
            >
              {discoveryPending ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />}
              Run discovery plugins
            </button>
          ) : null}
          {discoveryResult ? <div className="mt-2 text-xs text-terminal-green">Pipeline {titleCase(discoveryResult)}.</div> : null}
          {discoveryError ? <div className="mt-2 text-xs text-terminal-rose">{discoveryError}</div> : null}
        </div>

        <form
          className="space-y-3 border-t border-terminal-line pt-4 lg:border-l lg:border-t-0 lg:pl-5 lg:pt-0"
          onSubmit={(event) => {
            event.preventDefault();
            createProduct.mutate(
              {
                canonical_name: form.canonical_name,
                category: form.category || null,
                description: form.notes || null
              },
              {
                onSuccess: (created) => onSelect(created.id)
              }
            );
          }}
        >
          <h3 className="font-mono text-xs uppercase text-terminal-muted">Create candidate</h3>
          <div className="grid gap-2 sm:grid-cols-2">
            <Field label="Product keyword *">
              <input className={inputClass} required minLength={2} value={form.canonical_name} onChange={(event) => setForm({ ...form, canonical_name: event.target.value })} />
            </Field>
            <Field label="Category">
              <input className={inputClass} value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value })} />
            </Field>
            <Field label="Candidate source / session">
              <select className={inputClass} value={form.candidate_source} onChange={(event) => setForm({ ...form, candidate_source: event.target.value })}>
                <option value="manual">Manual input</option>
                <option value="amazon">Amazon research</option>
                <option value="poe_manual_import">POE manual import</option>
                <option value="csv">CSV import</option>
                <option value="supplier">Supplier source</option>
              </select>
            </Field>
            <Field label="Target margin / session">
              <select className={inputClass} value={form.target_margin} onChange={(event) => setForm({ ...form, target_margin: event.target.value })}>
                {[20, 30, 40, 50].map((value) => <option key={value} value={value}>{value}%</option>)}
              </select>
            </Field>
          </div>
          <Field label="Notes">
            <textarea className="min-h-16 w-full border border-terminal-line bg-terminal-bg px-2.5 py-2 text-sm outline-none focus:border-terminal-green" value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} />
          </Field>
          <div className="flex items-center gap-3">
            <button type="submit" disabled={createProduct.isPending} className="inline-flex h-9 items-center gap-2 border border-terminal-green/60 bg-terminal-green/10 px-3 text-sm text-terminal-green disabled:opacity-50">
              {createProduct.isPending ? <Loader2 size={15} className="animate-spin" /> : <Plus size={15} />}
              Create candidate
            </button>
            {createProduct.error ? <span className="text-xs text-terminal-rose">{createProduct.error.message}</span> : null}
          </div>
        </form>
      </div>
    </ValidationCard>
  );
}

function EconomicsStage({
  economics,
  modeled,
  targetMargin,
  setTargetMargin
}: {
  economics?: EconomicsValidator;
  modeled: CostScenario | null;
  targetMargin: number;
  setTargetMargin: (margin: number) => void;
}) {
  const sensitivity = economics?.sensitivity.filter((row) => row.target_margin_percent === targetMargin) ?? [];
  return (
    <ValidationCard
      title="03 / Economics"
      source={economics?.fee_source}
      updatedAt={economics?.updated_at}
      confidence={economics?.fee_source_confidence}
      missing={!modeled ? ["Selling price or Amazon fees"] : []}
      action={
        <select
          value={targetMargin}
          onChange={(event) => setTargetMargin(Number(event.target.value))}
          className="h-8 border border-terminal-line bg-terminal-bg px-2 text-xs outline-none focus:border-terminal-green"
          title="Session target margin"
        >
          {(economics?.scenarios.map((item) => item.target_margin_percent) ?? [20, 30, 40, 50]).map((margin) => (
            <option key={margin} value={margin}>{margin}% target margin</option>
          ))}
        </select>
      }
    >
      {modeled ? (
        <div className="space-y-4">
          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
            <Metric label="Modeled price" value={currency(modeled.selling_price)} />
            <Metric label="Amazon fees" value={currency(modeled.amazon_fees)} />
            <Metric label="Target profit" value={currency(modeled.target_profit)} />
            <Metric label="Max landed cost" value={currency(modeled.max_landed_cost)} tone="green" />
            <Metric label="Supplier landed" value={currency(modeled.supplier_landed_cost)} tone={modeled.decision === "quote_above_ceiling" ? "rose" : "neutral"} />
          </div>
          <WarningList warnings={economics?.warnings ?? []} />
          {sensitivity.length ? (
            <div className="overflow-x-auto border border-terminal-line bg-terminal-bg">
              <table className="w-full min-w-[620px] text-left text-sm">
                <thead className="bg-terminal-panel font-mono text-xs uppercase text-terminal-muted">
                  <tr>
                    <th className="border-b border-terminal-line px-3 py-2 font-medium">Price case</th>
                    <th className="border-b border-terminal-line px-3 py-2 font-medium">Selling price</th>
                    <th className="border-b border-terminal-line px-3 py-2 font-medium">Low fees ceiling</th>
                    <th className="border-b border-terminal-line px-3 py-2 font-medium">Modeled fees ceiling</th>
                    <th className="border-b border-terminal-line px-3 py-2 font-medium">High fees ceiling</th>
                  </tr>
                </thead>
                <tbody>
                  {sensitivity.map((row) => (
                    <tr key={row.price_label} className="border-b border-terminal-line/70 last:border-b-0">
                      <td className="px-3 py-2">{titleCase(row.price_label)}</td>
                      <td className="px-3 py-2 font-mono text-xs">{currency(row.selling_price)}</td>
                      <td className="px-3 py-2 font-mono text-xs">{currency(row.low_fees)}</td>
                      <td className="px-3 py-2 font-mono text-xs">{currency(row.modeled_fees)}</td>
                      <td className="px-3 py-2 font-mono text-xs">{currency(row.high_fees)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </div>
      ) : (
        <EmptyState label="Economics need Amazon price and fee evidence" />
      )}
    </ValidationCard>
  );
}

function SupplierStage({
  productId,
  quotes,
  validation
}: {
  productId: string;
  quotes: SupplierQuote[];
  validation?: SupplierValidation;
}) {
  return (
    <ValidationCard
      title="04 / Supplier quote"
      source={validation?.source}
      updatedAt={validation?.updated_at}
      confidence={quotes[0]?.confidence}
      missing={!quotes.length ? ["Supplier quote"] : []}
    >
      <div className="space-y-4">
        {quotes.length ? (
          <div className="overflow-x-auto border border-terminal-line bg-terminal-bg">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="bg-terminal-panel font-mono text-xs uppercase text-terminal-muted">
                <tr>
                  <th className="border-b border-terminal-line px-3 py-2 font-medium">Supplier</th>
                  <th className="border-b border-terminal-line px-3 py-2 font-medium">Landed</th>
                  <th className="border-b border-terminal-line px-3 py-2 font-medium">Ceiling</th>
                  <th className="border-b border-terminal-line px-3 py-2 font-medium">Safety</th>
                  <th className="border-b border-terminal-line px-3 py-2 font-medium">MOQ</th>
                  <th className="border-b border-terminal-line px-3 py-2 font-medium">Lead</th>
                  <th className="border-b border-terminal-line px-3 py-2 font-medium">Decision</th>
                </tr>
              </thead>
              <tbody>
                {quotes.map((quote) => (
                  <tr key={quote.id} className="border-b border-terminal-line/70 last:border-b-0">
                    <td className="px-3 py-2">{quote.supplier_name ?? "Unnamed supplier"}</td>
                    <td className="px-3 py-2 font-mono text-xs">{currency(quote.supplier_landed_cost, quote.currency)}</td>
                    <td className="px-3 py-2 font-mono text-xs">{currency(quote.max_landed_cost, quote.currency)}</td>
                    <td className={clsx("px-3 py-2 font-mono text-xs", (quote.margin_of_safety ?? 0) < 0 ? "text-terminal-rose" : "text-terminal-green")}>
                      {currency(quote.margin_of_safety, quote.currency)}
                    </td>
                    <td className="px-3 py-2 font-mono text-xs">{quote.moq ?? "--"}</td>
                    <td className="px-3 py-2 font-mono text-xs">{quote.lead_time_days ? `${quote.lead_time_days}d` : "--"}</td>
                    <td className="px-3 py-2"><DecisionBadge value={quote.decision} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
        {productId ? <SupplierQuoteForm productId={productId} /> : <EmptyState label="Select a product before adding a quote" />}
      </div>
    </ValidationCard>
  );
}

function ConstraintStage({
  productId,
  evaluation,
  pending,
  error,
  onEvaluate
}: {
  productId: string;
  evaluation?: ConstraintEvaluation;
  pending: boolean;
  error?: string;
  onEvaluate: () => void;
}) {
  return (
    <ValidationCard
      title="05 / Constraints"
      source={evaluation?.rule_profile_name}
      updatedAt={evaluation?.created_at}
      confidence={evaluation ? evaluation.constraint_score : null}
      missing={!evaluation ? ["Constraint evaluation"] : []}
      action={
        <button
          type="button"
          onClick={onEvaluate}
          disabled={!productId || pending}
          className="inline-flex h-8 items-center gap-2 border border-terminal-green/60 bg-terminal-green/10 px-2.5 text-xs text-terminal-green disabled:opacity-40"
        >
          {pending ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
          Apply default profile
        </button>
      }
    >
      {evaluation ? (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <DecisionBadge value={evaluation.eligible ? "pursue" : "skip"} />
            <span className="text-sm">{evaluation.explanation}</span>
            <span className="font-mono text-xs text-terminal-muted">{evaluation.constraint_score}/100 fit</span>
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <RuleList title="Hard failures" rows={evaluation.hard_failures} tone="rose" empty="No hard failures." />
            <RuleList title="Soft warnings" rows={evaluation.soft_warnings} tone="amber" empty="No soft warnings." />
          </div>
          {evaluation.risk_flags.length ? (
            <div className="flex flex-wrap gap-2">
              {evaluation.risk_flags.map((flag) => (
                <span key={flag.risk_type} className="inline-flex h-7 items-center border border-terminal-line bg-terminal-bg px-2 font-mono text-xs text-terminal-muted">
                  {titleCase(flag.risk_type)} / {flag.severity}
                </span>
              ))}
            </div>
          ) : null}
          {error ? <div className="text-xs text-terminal-rose">{error}</div> : null}
        </div>
      ) : (
        <EmptyState label={productId ? "Run the default rule profile" : "Select a product to evaluate constraints"} />
      )}
    </ValidationCard>
  );
}

function RuleList({
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
      <h3 className="mb-2 font-mono text-xs uppercase text-terminal-muted">{title}</h3>
      <div className="border border-terminal-line bg-terminal-bg">
        {rows.length ? rows.map((row) => (
          <div key={`${row.rule}-${row.message}`} className={clsx("flex gap-2 border-b border-terminal-line/70 px-3 py-2 text-sm last:border-b-0", tone === "rose" ? "text-terminal-rose" : "text-terminal-amber")}>
            <AlertTriangle size={14} className="mt-0.5 shrink-0" />
            <span>{row.message}</span>
          </div>
        )) : <div className="px-3 py-2 text-sm text-terminal-muted">{empty}</div>}
      </div>
    </div>
  );
}

function Metric({ label, value, tone = "neutral" }: { label: string; value: string; tone?: "neutral" | "green" | "rose" }) {
  return (
    <div className="border-l-2 border-terminal-line bg-terminal-bg px-3 py-2">
      <div className="font-mono text-[11px] uppercase text-terminal-muted">{label}</div>
      <div className={clsx("mt-1 font-mono text-base tabular-nums", tone === "green" ? "text-terminal-green" : tone === "rose" ? "text-terminal-rose" : "text-terminal-ink")}>{value}</div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block font-mono text-[11px] uppercase text-terminal-muted">{label}</span>
      {children}
    </label>
  );
}

function ActionButton({
  icon: Icon,
  label,
  onClick,
  pending
}: {
  icon: typeof Play;
  label: string;
  onClick: () => void;
  pending: boolean;
}) {
  return (
    <button type="button" onClick={onClick} disabled={pending} className="inline-flex h-8 items-center gap-2 border border-terminal-line bg-terminal-panel px-2.5 text-xs text-terminal-muted hover:text-terminal-ink disabled:opacity-40">
      <Icon size={13} className={pending ? "animate-spin" : ""} />
      {label}
    </button>
  );
}
