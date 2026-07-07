"use client";

import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { EmptyState } from "@/components/EmptyState";
import { OpportunityCard } from "@/components/OpportunityCard";
import { PluginRunTable } from "@/components/PluginRunTable";
import { RunPipelineButton } from "@/components/RunPipelineButton";
import { api } from "@/lib/api";

export default function DashboardPage() {
  const opportunities = useQuery({
    queryKey: ["opportunities", { limit: 8 }],
    queryFn: () => api.opportunities({ limit: 8 })
  });
  const runs = useQuery({
    queryKey: ["plugin-runs", 8],
    queryFn: () => api.pluginRuns(8)
  });

  const products = opportunities.data?.items ?? [];
  const distribution = buildDistribution(products.map((product) => product.latest_score ?? 0));
  const topScore = products[0]?.latest_score ?? null;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 border-b border-terminal-line pb-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="font-mono text-xs uppercase tracking-[0.24em] text-terminal-green">
            Product Discovery Terminal
          </div>
          <h1 className="mt-2 text-2xl font-semibold">Opportunity intelligence</h1>
        </div>
        <RunPipelineButton />
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Metric label="Products" value={String(opportunities.data?.total ?? 0)} />
        <Metric label="Top Score" value={topScore === null ? "--" : topScore.toFixed(1)} />
        <Metric label="Recent Runs" value={String(runs.data?.length ?? 0)} />
        <Metric label="Backend" value={opportunities.isError ? "offline" : "ready"} tone={opportunities.isError ? "rose" : "green"} />
      </div>

      <section className="grid gap-4 lg:grid-cols-[1.4fr_0.8fr]">
        <div>
          <SectionTitle title="Top Opportunities" />
          {opportunities.isLoading ? (
            <EmptyState label="Loading opportunities" />
          ) : products.length ? (
            <div className="grid gap-3 md:grid-cols-2">
              {products.slice(0, 4).map((product) => (
                <OpportunityCard key={product.id} product={product} />
              ))}
            </div>
          ) : (
            <EmptyState label="No scored opportunities yet" />
          )}
        </div>
        <div>
          <SectionTitle title="Score Distribution" />
          <div className="h-[277px] border border-terminal-line bg-terminal-panel/80 p-3">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={distribution}>
                <XAxis dataKey="bucket" stroke="#8e9aa5" fontSize={11} tickLine={false} axisLine={false} />
                <YAxis stroke="#8e9aa5" fontSize={11} tickLine={false} axisLine={false} allowDecimals={false} />
                <Tooltip
                  contentStyle={{
                    background: "#111315",
                    border: "1px solid #24282c",
                    color: "#e7ecef"
                  }}
                />
                <Bar dataKey="count" fill="#39d98a" radius={0} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>

      <section>
        <SectionTitle title="Recent Plugin Runs" />
        {runs.data?.length ? <PluginRunTable runs={runs.data} /> : <EmptyState label="No plugin runs recorded" />}
      </section>
    </div>
  );
}

function Metric({ label, value, tone = "neutral" }: { label: string; value: string; tone?: "neutral" | "green" | "rose" }) {
  const color = tone === "green" ? "text-terminal-green" : tone === "rose" ? "text-terminal-rose" : "text-terminal-ink";
  return (
    <div className="border border-terminal-line bg-terminal-panel/80 p-3">
      <div className="font-mono text-xs uppercase text-terminal-muted">{label}</div>
      <div className={`mt-2 font-mono text-2xl tabular-nums ${color}`}>{value}</div>
    </div>
  );
}

function SectionTitle({ title }: { title: string }) {
  return <h2 className="mb-3 font-mono text-xs uppercase tracking-[0.18em] text-terminal-muted">{title}</h2>;
}

function buildDistribution(scores: number[]) {
  const buckets = [
    { bucket: "0-29", count: 0 },
    { bucket: "30-49", count: 0 },
    { bucket: "50-69", count: 0 },
    { bucket: "70-84", count: 0 },
    { bucket: "85+", count: 0 }
  ];
  scores.forEach((score) => {
    if (score >= 85) buckets[4].count += 1;
    else if (score >= 70) buckets[3].count += 1;
    else if (score >= 50) buckets[2].count += 1;
    else if (score >= 30) buckets[1].count += 1;
    else buckets[0].count += 1;
  });
  return buckets;
}

