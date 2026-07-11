"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  Boxes,
  CheckCircle2,
  ExternalLink,
  Loader2,
  Play,
  Plus,
  RefreshCw,
  Search
} from "lucide-react";
import Link from "next/link";
import { type FormEvent, useMemo, useState } from "react";
import { EmptyState } from "@/components/EmptyState";
import { RecommendationBadge } from "@/components/RecommendationBadge";
import { api } from "@/lib/api";
import { dateTime, formatScore, titleCase } from "@/lib/format";
import type { CandidateCluster, DiscoveryRun, DiscoveryRunResult, SeedList } from "@/types/api";

const discoveryKeys = {
  seedLists: ["discovery", "seed-lists"] as const,
  runs: ["discovery", "runs"] as const
};

export default function DiscoveryPage() {
  const client = useQueryClient();
  const seedLists = useQuery({
    queryKey: discoveryKeys.seedLists,
    queryFn: api.seedLists
  });
  const runs = useQuery({
    queryKey: discoveryKeys.runs,
    queryFn: () => api.discoveryRuns(25)
  });
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [lastCreatedRun, setLastCreatedRun] = useState<DiscoveryRun | null>(null);

  const createSeedList = useMutation({
    mutationFn: api.createSeedList,
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: discoveryKeys.seedLists });
    }
  });
  const createRun = useMutation({
    mutationFn: api.createDiscoveryRun,
    onSuccess: async (run) => {
      setLastCreatedRun(run);
      setSelectedRunId(run.id);
      await Promise.all([
        client.invalidateQueries({ queryKey: discoveryKeys.runs }),
        client.invalidateQueries({ queryKey: ["products"] }),
        client.invalidateQueries({ queryKey: ["opportunities"] })
      ]);
    }
  });
  const selectedRun = useMemo(
    () =>
      runs.data?.find((run) => run.id === selectedRunId) ??
      (lastCreatedRun?.id === selectedRunId ? lastCreatedRun : undefined) ??
      runs.data?.[0],
    [lastCreatedRun, runs.data, selectedRunId]
  );

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 border-b border-terminal-line pb-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="font-mono text-xs uppercase tracking-[0.24em] text-terminal-green">Discovery</div>
          <h1 className="mt-2 text-2xl font-semibold">Product scanner</h1>
        </div>
        <button
          type="button"
          onClick={() => runs.refetch()}
          className="inline-flex h-10 items-center justify-center gap-2 border border-terminal-line bg-terminal-panel px-3 font-mono text-xs uppercase tracking-[0.12em] text-terminal-muted hover:border-terminal-green hover:text-terminal-green"
        >
          <RefreshCw size={14} />
          Refresh
        </button>
      </header>

      <div className="grid gap-6 xl:grid-cols-[420px_1fr]">
        <div className="space-y-6">
          <SeedListPanel
            seedLists={seedLists.data ?? []}
            isLoading={seedLists.isLoading}
            createPending={createSeedList.isPending}
            createError={createSeedList.error?.message}
            onCreate={(payload) => createSeedList.mutate(payload)}
          />
          <StartRunPanel
            seedLists={seedLists.data ?? []}
            isPending={createRun.isPending}
            error={createRun.error?.message}
            onStart={(payload) => createRun.mutate(payload)}
          />
          <RunHistoryPanel
            runs={runs.data ?? []}
            selectedRunId={selectedRun?.id}
            isLoading={runs.isLoading}
            onSelect={setSelectedRunId}
          />
        </div>

        <RunDetailPanel run={selectedRun} />
      </div>
    </div>
  );
}

function SeedListPanel({
  seedLists,
  isLoading,
  createPending,
  createError,
  onCreate
}: {
  seedLists: SeedList[];
  isLoading: boolean;
  createPending: boolean;
  createError?: string;
  onCreate: (payload: { name: string; keywords: { keyword: string }[] }) => void;
}) {
  const [name, setName] = useState("");
  const [keywords, setKeywords] = useState("");
  const parsedKeywords = parseKeywords(keywords);
  const canSubmit = name.trim().length >= 2 && parsedKeywords.length > 0 && !createPending;

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit) return;
    onCreate({
      name: name.trim(),
      keywords: parsedKeywords.map((keyword) => ({ keyword }))
    });
    setName("");
    setKeywords("");
  }

  return (
    <section className="border border-terminal-line bg-terminal-panel/70 p-4">
      <PanelTitle icon={Plus} title="Seed lists" />
      <form onSubmit={submit} className="mt-4 space-y-3">
        <input
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="Camping niches"
          className="h-10 w-full border border-terminal-line bg-terminal-bg px-3 text-sm outline-none placeholder:text-terminal-muted focus:border-terminal-green"
        />
        <textarea
          value={keywords}
          onChange={(event) => setKeywords(event.target.value)}
          placeholder={"camping cookware\ncamping storage\ncamping lighting"}
          rows={5}
          className="w-full resize-y border border-terminal-line bg-terminal-bg px-3 py-2 text-sm outline-none placeholder:text-terminal-muted focus:border-terminal-green"
        />
        <button
          type="submit"
          disabled={!canSubmit}
          className="inline-flex h-9 items-center justify-center gap-2 border border-terminal-green/70 bg-terminal-green/10 px-3 font-mono text-xs uppercase tracking-[0.12em] text-terminal-green hover:bg-terminal-green/15 disabled:cursor-not-allowed disabled:border-terminal-line disabled:bg-terminal-bg disabled:text-terminal-muted"
        >
          {createPending ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
          Save list
        </button>
      </form>
      {createError ? <ErrorLine message={createError} /> : null}
      <div className="mt-4 space-y-2">
        {isLoading ? (
          <EmptyState label="Loading seed lists" />
        ) : seedLists.length ? (
          seedLists.map((seedList) => (
            <div key={seedList.id} className="border border-terminal-line bg-terminal-bg p-3">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-sm font-medium">{titleCase(seedList.name)}</div>
                  <div className="mt-1 font-mono text-[11px] uppercase text-terminal-muted">
                    {seedList.keywords.length} keyword{seedList.keywords.length === 1 ? "" : "s"}
                  </div>
                </div>
                <span className="font-mono text-[11px] text-terminal-muted">{dateTime(seedList.created_at)}</span>
              </div>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {seedList.keywords.slice(0, 8).map((keyword) => (
                  <span key={keyword.id} className="border border-terminal-line px-2 py-1 font-mono text-[10px] text-terminal-muted">
                    {keyword.keyword}
                  </span>
                ))}
              </div>
            </div>
          ))
        ) : (
          <EmptyState label="No seed lists yet" />
        )}
      </div>
    </section>
  );
}

function StartRunPanel({
  seedLists,
  isPending,
  error,
  onStart
}: {
  seedLists: SeedList[];
  isPending: boolean;
  error?: string;
  onStart: (payload: {
    seed_list_id?: string | null;
    keywords?: { keyword: string }[];
    limit_per_keyword: number;
    enrich_top_n: number;
    min_cluster_confidence: number;
  }) => void;
}) {
  const [seedListId, setSeedListId] = useState("");
  const [keywords, setKeywords] = useState("");
  const [limit, setLimit] = useState("10");
  const [enrichTopN, setEnrichTopN] = useState("20");
  const [minConfidence, setMinConfidence] = useState("0.60");
  const parsedKeywords = parseKeywords(keywords);
  const canSubmit = Boolean(seedListId || parsedKeywords.length) && !isPending;

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit) return;
    onStart({
      seed_list_id: seedListId || null,
      keywords: seedListId ? [] : parsedKeywords.map((keyword) => ({ keyword })),
      limit_per_keyword: Math.max(1, Math.min(Number(limit) || 10, 50)),
      enrich_top_n: Math.max(0, Math.min(Number(enrichTopN) || 0, 100)),
      min_cluster_confidence: Math.max(0, Math.min(Number(minConfidence) || 0.6, 1))
    });
  }

  return (
    <section className="border border-terminal-line bg-terminal-panel/70 p-4">
      <PanelTitle icon={Play} title="Start run" />
      <form onSubmit={submit} className="mt-4 space-y-3">
        <select
          value={seedListId}
          onChange={(event) => setSeedListId(event.target.value)}
          className="h-10 w-full border border-terminal-line bg-terminal-bg px-3 text-sm outline-none focus:border-terminal-green"
        >
          <option value="">Ad hoc keywords</option>
          {seedLists.map((seedList) => (
            <option key={seedList.id} value={seedList.id}>
              {seedList.name}
            </option>
          ))}
        </select>
        {!seedListId ? (
          <textarea
            value={keywords}
            onChange={(event) => setKeywords(event.target.value)}
            placeholder={"travel organizer\ncamping cookware"}
            rows={4}
            className="w-full resize-y border border-terminal-line bg-terminal-bg px-3 py-2 text-sm outline-none placeholder:text-terminal-muted focus:border-terminal-green"
          />
        ) : null}
        <div className="grid gap-3 sm:grid-cols-3">
          <label className="block">
            <span className="mb-1 block font-mono text-[11px] uppercase text-terminal-muted">Limit/keyword</span>
            <input
              value={limit}
              onChange={(event) => setLimit(event.target.value)}
              inputMode="numeric"
              className="h-10 w-full border border-terminal-line bg-terminal-bg px-3 text-sm outline-none focus:border-terminal-green"
            />
          </label>
          <label className="block">
            <span className="mb-1 block font-mono text-[11px] uppercase text-terminal-muted">Enrich top N</span>
            <input
              value={enrichTopN}
              onChange={(event) => setEnrichTopN(event.target.value)}
              inputMode="numeric"
              className="h-10 w-full border border-terminal-line bg-terminal-bg px-3 text-sm outline-none focus:border-terminal-green"
            />
          </label>
          <label className="block">
            <span className="mb-1 block font-mono text-[11px] uppercase text-terminal-muted">Min confidence</span>
            <input
              value={minConfidence}
              onChange={(event) => setMinConfidence(event.target.value)}
              inputMode="decimal"
              className="h-10 w-full border border-terminal-line bg-terminal-bg px-3 text-sm outline-none focus:border-terminal-green"
            />
          </label>
        </div>
        <button
          type="submit"
          disabled={!canSubmit}
          className="inline-flex h-10 items-center justify-center gap-2 border border-terminal-green/70 bg-terminal-green/10 px-3 font-mono text-xs uppercase tracking-[0.12em] text-terminal-green hover:bg-terminal-green/15 disabled:cursor-not-allowed disabled:border-terminal-line disabled:bg-terminal-bg disabled:text-terminal-muted"
        >
          {isPending ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />}
          Run scanner
        </button>
      </form>
      {error ? <ErrorLine message={error} /> : null}
    </section>
  );
}

function RunHistoryPanel({
  runs,
  selectedRunId,
  isLoading,
  onSelect
}: {
  runs: DiscoveryRun[];
  selectedRunId?: string;
  isLoading: boolean;
  onSelect: (runId: string) => void;
}) {
  return (
    <section className="border border-terminal-line bg-terminal-panel/70 p-4">
      <PanelTitle icon={RefreshCw} title="Recent runs" />
      <div className="mt-4 space-y-2">
        {isLoading ? (
          <EmptyState label="Loading discovery runs" />
        ) : runs.length ? (
          runs.map((run) => (
            <button
              key={run.id}
              type="button"
              onClick={() => onSelect(run.id)}
              className={`block w-full border px-3 py-2 text-left ${
                selectedRunId === run.id
                  ? "border-terminal-green/60 bg-terminal-green/10"
                  : "border-terminal-line bg-terminal-bg hover:border-terminal-green/40"
              }`}
            >
              <div className="flex items-center justify-between gap-3">
                <StatusBadge value={run.status} />
                <span className="font-mono text-[11px] text-terminal-muted">{dateTime(run.started_at)}</span>
              </div>
              <div className="mt-2 font-mono text-[11px] uppercase text-terminal-muted">
                {numberSummary(run, "keywords_requested")} keywords / {numberSummary(run, "results_created")} results
              </div>
            </button>
          ))
        ) : (
          <EmptyState label="No discovery runs yet" />
        )}
      </div>
    </section>
  );
}

function RunDetailPanel({ run }: { run?: DiscoveryRun }) {
  if (!run) {
    return <EmptyState label="No discovery run selected" />;
  }

  const errors = summaryErrors(run);
  return (
    <div className="space-y-6">
      <section className="border border-terminal-line bg-terminal-panel/70 p-4">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <PanelTitle icon={Boxes} title="Run status" />
            <div className="mt-3 flex flex-wrap gap-2">
              <StatusBadge value={run.status} />
              <span className="border border-terminal-line px-2 py-1 font-mono text-xs uppercase text-terminal-muted">
                {String(run.summary.enrichment_state ?? "unknown")}
              </span>
              <span className="border border-terminal-line px-2 py-1 font-mono text-xs text-terminal-muted">
                enrich top {numberSummary(run, "enrichment_top_n")}
              </span>
              <span className="border border-terminal-line px-2 py-1 font-mono text-xs text-terminal-muted">
                min conf {formatConfidence(run.summary.min_cluster_confidence)}
              </span>
              {run.source_plugins.map((plugin) => (
                <span key={plugin} className="border border-terminal-line px-2 py-1 font-mono text-xs text-terminal-muted">
                  {plugin}
                </span>
              ))}
            </div>
          </div>
          <div className="font-mono text-xs text-terminal-muted">
            <div>Started {dateTime(run.started_at)}</div>
            <div>Finished {dateTime(run.finished_at)}</div>
          </div>
        </div>

        <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Metric label="Seed keywords" value={numberSummary(run, "keywords_requested")} />
          <Metric label="Clusters" value={run.clusters.length} />
          <Metric label="Created" value={numberSummary(run, "candidates_created")} tone="green" />
          <Metric label="Matched" value={numberSummary(run, "candidates_matched")} tone="amber" />
          <Metric label="Results" value={run.results.length} />
          <Metric label="Origins" value={run.origins.length} />
          <Metric label="Enriched" value={numberSummary(run, "enriched_candidates")} tone="green" />
          <Metric label="Enrich failed" value={numberSummary(run, "enrichment_failed")} tone={numberSummary(run, "enrichment_failed") ? "rose" : "neutral"} />
          <Metric label="Rejected" value={numberSummary(run, "rejected_results")} />
          <Metric label="Failed" value={numberSummary(run, "keywords_failed")} tone={errors.length ? "rose" : "neutral"} />
        </div>

        {errors.length ? (
          <div className="mt-4 border border-terminal-rose/50 bg-terminal-rose/5 p-3 text-sm text-terminal-rose">
            <div className="mb-2 flex items-center gap-2 font-mono text-xs uppercase">
              <AlertTriangle size={14} />
              Errors
            </div>
            <div className="space-y-1 text-xs">
              {errors.slice(0, 6).map((message) => (
                <div key={message}>{message}</div>
              ))}
            </div>
          </div>
        ) : null}
      </section>

      <section className="border border-terminal-line bg-terminal-panel/70 p-4">
        <PanelTitle icon={Boxes} title="Clusters found" />
        {run.clusters.length ? (
          <div className="mt-4 grid gap-3 lg:grid-cols-2">
            {run.clusters.map((cluster) => (
              <ClusterCard key={cluster.id} cluster={cluster} results={run.results} />
            ))}
          </div>
        ) : (
          <EmptyState label="No clusters found" />
        )}
      </section>

      <section className="border border-terminal-line bg-terminal-panel/70 p-4">
        <PanelTitle icon={CheckCircle2} title="Candidates" />
        {run.results.length ? (
          <div className="mt-4 overflow-x-auto border border-terminal-line bg-terminal-bg">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="bg-terminal-panel font-mono text-xs uppercase text-terminal-muted">
                <tr>
                  <th className="border-b border-terminal-line px-3 py-2 font-medium">Rank</th>
                  <th className="border-b border-terminal-line px-3 py-2 font-medium">Candidate</th>
                  <th className="border-b border-terminal-line px-3 py-2 font-medium">Score</th>
                  <th className="border-b border-terminal-line px-3 py-2 font-medium">Recommendation</th>
                  <th className="border-b border-terminal-line px-3 py-2 font-medium">Status</th>
                  <th className="border-b border-terminal-line px-3 py-2 font-medium" aria-label="Open" />
                </tr>
              </thead>
              <tbody>
                {run.results.map((result) => (
                  <tr key={result.id} className="border-b border-terminal-line/70 last:border-b-0">
                    <td className="px-3 py-2 font-mono text-xs tabular-nums">{result.rank_position ?? "--"}</td>
                    <td className="px-3 py-2 font-medium">{titleCase(result.product_name)}</td>
                    <td className="px-3 py-2 font-mono text-xs tabular-nums">{formatScore(result.opportunity_score)}</td>
                    <td className="px-3 py-2"><RecommendationBadge value={result.recommendation} /></td>
                    <td className="px-3 py-2 font-mono text-xs uppercase text-terminal-muted">{titleCase(result.status)}</td>
                    <td className="px-3 py-2">
                      <Link
                        href={`/products/${result.product_id}`}
                        className="inline-flex h-8 w-8 items-center justify-center border border-terminal-line text-terminal-muted hover:border-terminal-green hover:text-terminal-green"
                        aria-label={`Open ${result.product_name}`}
                      >
                        <ExternalLink size={14} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState label="No candidates created" />
        )}
      </section>
    </div>
  );
}

function ClusterCard({
  cluster,
  results
}: {
  cluster: CandidateCluster;
  results: DiscoveryRunResult[];
}) {
  const linkedResults = results.filter((result) => result.candidate_cluster_id === cluster.id);
  return (
    <div className="border border-terminal-line bg-terminal-bg p-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-medium">{titleCase(cluster.label)}</div>
          <div className="mt-1 font-mono text-[11px] uppercase text-terminal-muted">
            {cluster.source_query}
          </div>
        </div>
        <span className="font-mono text-[11px] text-terminal-muted">
          {cluster.evidence_observation_ids.length} obs
        </span>
      </div>
      <div className="mt-3 space-y-1">
        {linkedResults.map((result) => (
          <Link
            key={result.id}
            href={`/products/${result.product_id}`}
            className="flex items-center justify-between gap-3 border border-terminal-line px-2 py-1.5 text-xs hover:border-terminal-green hover:text-terminal-green"
          >
            <span>{titleCase(result.product_name)}</span>
            <span className="font-mono tabular-nums">{formatScore(result.opportunity_score)}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}

function PanelTitle({ icon: Icon, title }: { icon: typeof Boxes; title: string }) {
  return (
    <div className="flex items-center gap-2 font-mono text-xs uppercase tracking-[0.18em] text-terminal-muted">
      <Icon size={14} className="text-terminal-green" />
      {title}
    </div>
  );
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
    <div className="border border-terminal-line bg-terminal-bg p-3">
      <div className="font-mono text-[11px] uppercase text-terminal-muted">{label}</div>
      <div className={`mt-1 font-mono text-xl tabular-nums ${color}`}>{value}</div>
    </div>
  );
}

function StatusBadge({ value }: { value: string }) {
  const tone =
    value === "success"
      ? "border-terminal-green/60 bg-terminal-green/10 text-terminal-green"
      : value === "failed"
        ? "border-terminal-rose/60 bg-terminal-rose/10 text-terminal-rose"
        : "border-terminal-amber/60 bg-terminal-amber/10 text-terminal-amber";
  return (
    <span className={`inline-flex h-7 items-center border px-2 font-mono text-xs uppercase ${tone}`}>
      {titleCase(value)}
    </span>
  );
}

function ErrorLine({ message }: { message: string }) {
  return <div className="mt-3 text-xs text-terminal-rose">{message}</div>;
}

function parseKeywords(value: string) {
  return Array.from(
    new Set(
      value
        .split(/\n|,/)
        .map((item) => item.trim().toLowerCase())
        .filter((item) => item.length >= 2)
    )
  );
}

function numberSummary(run: DiscoveryRun, key: string) {
  const value = run.summary[key];
  return typeof value === "number" ? value : 0;
}

function formatConfidence(value: unknown) {
  return typeof value === "number" ? value.toFixed(2) : "--";
}

function summaryErrors(run: DiscoveryRun) {
  const errors = Array.isArray(run.summary.errors)
    ? run.summary.errors.filter((item): item is string => typeof item === "string")
    : [];
  if (run.error_message && !errors.includes(run.error_message)) {
    return [run.error_message, ...errors];
  }
  return errors;
}
