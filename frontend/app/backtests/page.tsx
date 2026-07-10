"use client";

import clsx from "clsx";
import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  ClipboardCheck,
  Loader2,
  Target
} from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { EmptyState } from "@/components/EmptyState";
import { DecisionBadge } from "@/components/validation/ValidationCard";
import { dateTime, percent, titleCase } from "@/lib/format";
import {
  useAddPaperTradeOutcome,
  useBacktestSummary,
  usePaperTrades
} from "@/lib/validation-hooks";
import type { OutcomeInput, OutcomeLabel, PaperTrade } from "@/types/api";

const inputClass =
  "h-9 w-full border border-terminal-line bg-terminal-bg px-2.5 text-sm outline-none placeholder:text-terminal-muted focus:border-terminal-green";

export default function BacktestsPage() {
  const trades = usePaperTrades();
  const summary = useBacktestSummary();
  const [selectedTradeId, setSelectedTradeId] = useState("");
  const items = useMemo(() => trades.data ?? [], [trades.data]);

  useEffect(() => {
    if (!selectedTradeId && items.length) setSelectedTradeId(items[0].id);
  }, [items, selectedTradeId]);

  const selectedTrade = items.find((trade) => trade.id === selectedTradeId);
  const openTrades = items.filter((trade) => trade.status === "open");
  const falsePositives = useMemo(
    () =>
      items.filter(
        (trade) =>
          trade.decision === "paper_pursue" &&
          trade.outcomes.some((outcome) => ["deteriorated", "invalidated"].includes(outcome.outcome_label))
      ),
    [items]
  );
  const falseNegatives = useMemo(
    () =>
      items.filter(
        (trade) =>
          trade.decision === "paper_skip" &&
          trade.outcomes.some((outcome) => outcome.outcome_label === "improved")
      ),
    [items]
  );

  return (
    <div className="space-y-6">
      <header className="border-b border-terminal-line pb-5">
        <div className="font-mono text-xs uppercase tracking-[0.24em] text-terminal-green">Backtests</div>
        <div className="mt-2 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-2xl font-semibold">Paper trading outcomes</h1>
            <p className="mt-1 text-sm text-terminal-muted">Frozen decisions measured against later market evidence.</p>
          </div>
          <span className="font-mono text-xs text-terminal-muted">
            {summary.data?.total_outcomes ?? 0} outcomes / {summary.data?.total_paper_trades ?? 0} trades
          </span>
        </div>
      </header>

      {summary.isError ? (
        <Notice tone="rose" text={`Backtest summary unavailable: ${summary.error.message}`} />
      ) : null}

      <section>
        <SectionTitle title="Backtest summary" />
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
          <Metric label="Paper trades" value={String(summary.data?.total_paper_trades ?? 0)} icon={Target} />
          <Metric label="Outcomes" value={String(summary.data?.total_outcomes ?? 0)} icon={ClipboardCheck} />
          <Metric label="Pursue improved" value={rate(summary.data?.top_picks_improved_rate)} icon={BarChart3} tone="green" />
          <Metric label="Watch improved" value={rate(summary.data?.watch_picks_improved_rate)} icon={BarChart3} />
          <Metric label="Skip improved" value={rate(summary.data?.skip_picks_improved_rate)} icon={BarChart3} tone="rose" />
        </div>
      </section>

      <section className="grid gap-5 xl:grid-cols-[minmax(0,1.25fr)_minmax(360px,0.75fr)]">
        <div>
          <SectionTitle title="Open paper trades" />
          {trades.isLoading ? (
            <EmptyState label="Loading paper trades" />
          ) : openTrades.length ? (
            <TradeTable trades={openTrades} selectedTradeId={selectedTradeId} onSelect={setSelectedTradeId} />
          ) : (
            <EmptyState label="No open paper trades" />
          )}
        </div>
        <div>
          <SectionTitle title="Outcome entry" />
          <div className="border border-terminal-line bg-terminal-panel/80 p-4">
            {selectedTrade ? (
              <OutcomeForm key={selectedTrade.id} trade={selectedTrade} />
            ) : (
              <EmptyState label="Select a paper trade" />
            )}
          </div>
        </div>
      </section>

      <section>
        <SectionTitle title="Evaluation schedule" />
        {items.length ? (
          <div className="overflow-x-auto border border-terminal-line bg-terminal-bg">
            <table className="w-full min-w-[780px] text-left text-sm">
              <thead className="bg-terminal-panel font-mono text-xs uppercase text-terminal-muted">
                <tr>
                  <th className="border-b border-terminal-line px-3 py-2 font-medium">Product</th>
                  <th className="border-b border-terminal-line px-3 py-2 font-medium">Entry</th>
                  <th className="border-b border-terminal-line px-3 py-2 font-medium">30 day</th>
                  <th className="border-b border-terminal-line px-3 py-2 font-medium">60 day</th>
                  <th className="border-b border-terminal-line px-3 py-2 font-medium">90 day</th>
                  <th className="border-b border-terminal-line px-3 py-2 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {items.map((trade) => (
                  <tr key={trade.id} className="border-b border-terminal-line/70 last:border-b-0">
                    <td className="px-3 py-2">
                      <Link className="font-medium hover:text-terminal-green" href={`/products/${trade.product_id}`}>
                        {titleCase(trade.snapshot.canonical_name)}
                      </Link>
                    </td>
                    <td className="px-3 py-2 font-mono text-xs text-terminal-muted">{dateTime(trade.entry_date)}</td>
                    {[30, 60, 90].map((window) => (
                      <td key={window} className="px-3 py-2">
                        <WindowStatus trade={trade} window={window} />
                      </td>
                    ))}
                    <td className="px-3 py-2 font-mono text-xs uppercase text-terminal-muted">{trade.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState label="No evaluation windows scheduled" />
        )}
      </section>

      <section className="grid gap-5 xl:grid-cols-2">
        <div>
          <SectionTitle title="Discovery source performance" />
          <PerformanceTable rows={summary.data?.average_outcome_by_discovery_source ?? {}} />
        </div>
        <div>
          <SectionTitle title="Decision performance" />
          <PerformanceTable rows={summary.data?.average_outcome_by_recommendation ?? {}} />
        </div>
      </section>

      <section className="grid gap-5 xl:grid-cols-2">
        <ReviewQueue title="False positives" trades={falsePositives} empty="No pursue decisions have deteriorated or been invalidated." tone="rose" />
        <ReviewQueue title="False negatives" trades={falseNegatives} empty="No skipped decisions have later improved." tone="amber" />
      </section>

      <Notice
        tone="amber"
        text="Paper outcomes inform review only. They do not retrain scoring or execute buy, sell, or sourcing decisions."
      />
    </div>
  );
}

function OutcomeForm({ trade }: { trade: PaperTrade }) {
  const addOutcome = useAddPaperTradeOutcome();
  const completedWindows = new Set(trade.outcomes.map((outcome) => outcome.window_days));
  const nextWindow = trade.evaluation_windows.find((window) => !completedWindows.has(window)) ?? 90;
  const [form, setForm] = useState({
    window_days: String(nextWindow),
    outcome_label: "insufficient_data" as OutcomeLabel,
    outcome_score: "",
    price_change: "",
    review_count_change: "",
    rank_change: "",
    search_interest_change: "",
    seller_count_change: "",
    supplier_cost_change: "",
    constraint_status_change: "",
    notes: ""
  });

  function update(key: keyof typeof form, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  return (
    <form
      className="space-y-3"
      onSubmit={(event) => {
        event.preventDefault();
        const input: OutcomeInput = {
          window_days: Number(form.window_days),
          outcome_label: form.outcome_label,
          outcome_score: optionalNumber(form.outcome_score),
          price_change: optionalNumber(form.price_change),
          review_count_change: optionalNumber(form.review_count_change),
          rank_change: optionalNumber(form.rank_change),
          search_interest_change: optionalNumber(form.search_interest_change),
          seller_count_change: optionalNumber(form.seller_count_change),
          supplier_cost_change: optionalNumber(form.supplier_cost_change),
          constraint_status_change: form.constraint_status_change || null,
          notes: form.notes || null
        };
        addOutcome.mutate({ id: trade.id, input });
      }}
    >
      <div className="border-b border-terminal-line pb-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <Link href={`/products/${trade.product_id}`} className="font-medium hover:text-terminal-green">
            {titleCase(trade.snapshot.canonical_name)}
          </Link>
          <DecisionBadge value={trade.decision} />
        </div>
        <p className="mt-2 line-clamp-2 text-xs leading-5 text-terminal-muted">{trade.hypothesis || "No hypothesis recorded."}</p>
      </div>

      <div className="grid gap-2 sm:grid-cols-2">
        <Field label="Window">
          <select className={inputClass} value={form.window_days} onChange={(event) => update("window_days", event.target.value)}>
            {trade.evaluation_windows.map((window) => (
              <option key={window} value={window}>{window} days{completedWindows.has(window) ? " / recorded" : ""}</option>
            ))}
          </select>
        </Field>
        <Field label="Outcome">
          <select className={inputClass} value={form.outcome_label} onChange={(event) => setForm({ ...form, outcome_label: event.target.value as OutcomeLabel })}>
            <option value="improved">Improved</option>
            <option value="flat">Flat</option>
            <option value="deteriorated">Deteriorated</option>
            <option value="invalidated">Invalidated</option>
            <option value="insufficient_data">Insufficient data</option>
          </select>
        </Field>
      </div>

      <div className="grid gap-2 sm:grid-cols-3">
        <NumericField label="Outcome score" value={form.outcome_score} onChange={(value) => update("outcome_score", value)} min="-100" max="100" />
        <NumericField label="Price change %" value={form.price_change} onChange={(value) => update("price_change", value)} />
        <NumericField label="Reviews change" value={form.review_count_change} onChange={(value) => update("review_count_change", value)} />
        <NumericField label="Rank change" value={form.rank_change} onChange={(value) => update("rank_change", value)} />
        <NumericField label="Search change %" value={form.search_interest_change} onChange={(value) => update("search_interest_change", value)} />
        <NumericField label="Seller change" value={form.seller_count_change} onChange={(value) => update("seller_count_change", value)} />
        <NumericField label="Supplier cost %" value={form.supplier_cost_change} onChange={(value) => update("supplier_cost_change", value)} />
        <Field label="Constraint status">
          <input className={inputClass} value={form.constraint_status_change} onChange={(event) => update("constraint_status_change", event.target.value)} placeholder="unchanged" />
        </Field>
      </div>

      <Field label="Notes">
        <textarea className="min-h-16 w-full resize-y border border-terminal-line bg-terminal-bg px-2.5 py-2 text-sm outline-none focus:border-terminal-green" value={form.notes} onChange={(event) => update("notes", event.target.value)} />
      </Field>

      <div className="flex flex-wrap items-center gap-3">
        <button type="submit" disabled={addOutcome.isPending} className="inline-flex h-9 items-center gap-2 border border-terminal-green/60 bg-terminal-green/10 px-3 text-sm text-terminal-green disabled:opacity-50">
          {addOutcome.isPending ? <Loader2 size={15} className="animate-spin" /> : <ClipboardCheck size={15} />}
          Record outcome
        </button>
        {addOutcome.error ? <span className="text-xs text-terminal-rose">{addOutcome.error.message}</span> : null}
        {addOutcome.isSuccess ? <span className="text-xs text-terminal-green">Outcome recorded.</span> : null}
      </div>
    </form>
  );
}

function TradeTable({
  trades,
  selectedTradeId,
  onSelect
}: {
  trades: PaperTrade[];
  selectedTradeId: string;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="overflow-x-auto border border-terminal-line bg-terminal-bg">
      <table className="w-full min-w-[680px] text-left text-sm">
        <thead className="bg-terminal-panel font-mono text-xs uppercase text-terminal-muted">
          <tr>
            <th className="border-b border-terminal-line px-3 py-2 font-medium">Product</th>
            <th className="border-b border-terminal-line px-3 py-2 font-medium">Decision</th>
            <th className="border-b border-terminal-line px-3 py-2 font-medium">Source</th>
            <th className="border-b border-terminal-line px-3 py-2 font-medium">Entry</th>
            <th className="border-b border-terminal-line px-3 py-2 font-medium">Outcomes</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((trade) => (
            <tr
              key={trade.id}
              onClick={() => onSelect(trade.id)}
              className={clsx(
                "cursor-pointer border-b border-terminal-line/70 last:border-b-0",
                selectedTradeId === trade.id ? "bg-terminal-green/10" : "hover:bg-terminal-panel/70"
              )}
            >
              <td className="px-3 py-2 font-medium">{titleCase(trade.snapshot.canonical_name)}</td>
              <td className="px-3 py-2"><DecisionBadge value={trade.decision} /></td>
              <td className="px-3 py-2 text-terminal-muted">{titleCase(trade.snapshot.discovery_source)}</td>
              <td className="px-3 py-2 font-mono text-xs text-terminal-muted">{dateTime(trade.entry_date)}</td>
              <td className="px-3 py-2 font-mono text-xs">{trade.outcomes.length}/{trade.evaluation_windows.length}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PerformanceTable({
  rows
}: {
  rows: Record<string, { count: number; measured_count: number; improved_rate: number | null; average_outcome_score: number | null }>;
}) {
  const entries = Object.entries(rows);
  if (!entries.length) return <EmptyState label="No measured outcomes" />;
  return (
    <div className="border border-terminal-line bg-terminal-bg">
      {entries.map(([name, row]) => (
        <div key={name} className="grid grid-cols-[1fr_70px_90px_80px] items-center gap-2 border-b border-terminal-line/70 px-3 py-2 text-sm last:border-b-0">
          <span className="truncate">{titleCase(name)}</span>
          <span className="font-mono text-xs text-terminal-muted">{row.measured_count}/{row.count}</span>
          <span className="font-mono text-xs">{rate(row.improved_rate)}</span>
          <span className="text-right font-mono text-xs">{row.average_outcome_score?.toFixed(1) ?? "--"}</span>
        </div>
      ))}
    </div>
  );
}

function ReviewQueue({
  title,
  trades,
  empty,
  tone
}: {
  title: string;
  trades: PaperTrade[];
  empty: string;
  tone: "rose" | "amber";
}) {
  return (
    <div>
      <SectionTitle title={title} />
      <div className="border border-terminal-line bg-terminal-bg">
        {trades.length ? trades.map((trade) => (
          <Link key={trade.id} href={`/products/${trade.product_id}`} className="flex items-center gap-3 border-b border-terminal-line/70 px-3 py-2 text-sm last:border-b-0 hover:bg-terminal-panel">
            <AlertTriangle size={14} className={tone === "rose" ? "text-terminal-rose" : "text-terminal-amber"} />
            <span>{titleCase(trade.snapshot.canonical_name)}</span>
            <span className="ml-auto font-mono text-xs text-terminal-muted">{titleCase(trade.outcomes.at(-1)?.outcome_label)}</span>
          </Link>
        )) : <div className="px-3 py-4 text-sm text-terminal-muted">{empty}</div>}
      </div>
    </div>
  );
}

function WindowStatus({ trade, window }: { trade: PaperTrade; window: number }) {
  if (!trade.evaluation_windows.includes(window)) return <span className="font-mono text-xs text-terminal-muted">N/A</span>;
  const outcome = trade.outcomes.find((item) => item.window_days === window);
  if (!outcome) return <span className="font-mono text-xs text-terminal-amber">Waiting</span>;
  return (
    <span className={clsx("inline-flex items-center gap-1 font-mono text-xs", outcome.outcome_label === "improved" ? "text-terminal-green" : outcome.outcome_label === "flat" ? "text-terminal-muted" : "text-terminal-rose")}>
      <CheckCircle2 size={12} />
      {titleCase(outcome.outcome_label)}
    </span>
  );
}

function Metric({
  label,
  value,
  icon: Icon,
  tone = "neutral"
}: {
  label: string;
  value: string;
  icon: typeof Target;
  tone?: "neutral" | "green" | "rose";
}) {
  return (
    <div className="border border-terminal-line bg-terminal-panel/80 p-3">
      <div className="flex items-center justify-between font-mono text-xs uppercase text-terminal-muted">
        <span>{label}</span>
        <Icon size={14} />
      </div>
      <div className={clsx("mt-2 font-mono text-xl tabular-nums", tone === "green" ? "text-terminal-green" : tone === "rose" ? "text-terminal-rose" : "text-terminal-ink")}>{value}</div>
    </div>
  );
}

function NumericField({
  label,
  value,
  onChange,
  min,
  max
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  min?: string;
  max?: string;
}) {
  return (
    <Field label={label}>
      <input className={inputClass} type="number" step="0.01" min={min} max={max} value={value} onChange={(event) => onChange(event.target.value)} />
    </Field>
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

function Notice({ tone, text }: { tone: "amber" | "rose"; text: string }) {
  return (
    <div className={clsx("flex items-start gap-2 border px-3 py-2 text-xs", tone === "rose" ? "border-terminal-rose/40 bg-terminal-rose/5 text-terminal-rose" : "border-terminal-amber/40 bg-terminal-amber/5 text-terminal-amber")}>
      <AlertTriangle size={14} className="mt-0.5 shrink-0" />
      <span>{text}</span>
    </div>
  );
}

function SectionTitle({ title }: { title: string }) {
  return <h2 className="mb-3 font-mono text-xs uppercase tracking-[0.18em] text-terminal-muted">{title}</h2>;
}

function rate(value: number | null | undefined) {
  return value === null || value === undefined ? "--" : percent(value);
}

function optionalNumber(value: string) {
  return value === "" ? null : Number(value);
}
