"use client";

import { useQuery } from "@tanstack/react-query";
import { EmptyState } from "@/components/EmptyState";
import { PluginRunTable } from "@/components/PluginRunTable";
import { api } from "@/lib/api";

export default function PluginsPage() {
  const plugins = useQuery({ queryKey: ["plugins"], queryFn: api.plugins });
  const runs = useQuery({ queryKey: ["plugin-runs", 20], queryFn: () => api.pluginRuns(20) });

  return (
    <div className="space-y-6">
      <div className="border-b border-terminal-line pb-5">
        <div className="font-mono text-xs uppercase tracking-[0.24em] text-terminal-green">Plugins</div>
        <h1 className="mt-2 text-2xl font-semibold">Installed plugin catalog</h1>
      </div>

      {plugins.data ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <PluginGroup title="Ingestion" plugins={plugins.data.ingestion} />
          <PluginGroup title="Analyzers" plugins={plugins.data.analyzers} />
        </div>
      ) : (
        <EmptyState label="Loading plugins" />
      )}

      <section className="space-y-3">
        <h2 className="font-mono text-xs uppercase tracking-[0.18em] text-terminal-muted">Latest Runs</h2>
        {runs.data?.length ? <PluginRunTable runs={runs.data} /> : <EmptyState label="No runs recorded" />}
      </section>
    </div>
  );
}

function PluginGroup({
  title,
  plugins
}: {
  title: string;
  plugins: Array<{
    name: string;
    version: string;
    enabled?: boolean;
    configured?: boolean | null;
    environment?: string | null;
    missing_credentials?: string[];
    description: string | null;
    supports: string[];
  }>;
}) {
  return (
    <section className="border border-terminal-line bg-terminal-bg">
      <div className="border-b border-terminal-line bg-terminal-panel px-4 py-3 font-mono text-xs uppercase tracking-[0.18em] text-terminal-muted">
        {title}
      </div>
      <div>
        {plugins.map((plugin) => (
          <div key={plugin.name} className="border-b border-terminal-line p-4 last:border-b-0">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="font-medium">{plugin.name}</h3>
                <p className="mt-1 text-sm leading-6 text-terminal-muted">{plugin.description}</p>
              </div>
              <div className="text-right">
                <span className="font-mono text-xs text-terminal-green">{plugin.version}</span>
                {plugin.environment ? (
                  <div className="mt-1 font-mono text-xs uppercase text-terminal-muted">{plugin.environment}</div>
                ) : null}
              </div>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {plugin.configured === false ? (
                <span className="border border-terminal-amber/50 px-2 py-1 font-mono text-xs text-terminal-amber">
                  missing config
                </span>
              ) : null}
              {plugin.supports.map((support) => (
                <span key={support} className="border border-terminal-line px-2 py-1 font-mono text-xs text-terminal-muted">
                  {support}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
