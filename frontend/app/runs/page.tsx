"use client";

import { useQuery } from "@tanstack/react-query";
import { EmptyState } from "@/components/EmptyState";
import { PluginRunTable } from "@/components/PluginRunTable";
import { RunPipelineButton } from "@/components/RunPipelineButton";
import { api } from "@/lib/api";

export default function RunsPage() {
  const runs = useQuery({ queryKey: ["plugin-runs", 100], queryFn: () => api.pluginRuns(100) });

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 border-b border-terminal-line pb-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="font-mono text-xs uppercase tracking-[0.24em] text-terminal-green">Runs</div>
          <h1 className="mt-2 text-2xl font-semibold">Pipeline execution history</h1>
        </div>
        <RunPipelineButton />
      </div>

      {runs.data?.length ? <PluginRunTable runs={runs.data} /> : <EmptyState label="No pipeline runs recorded" />}
    </div>
  );
}

