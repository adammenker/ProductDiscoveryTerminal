"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Play, RefreshCw } from "lucide-react";
import { api } from "@/lib/api";

export function RunPipelineButton() {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: api.runPipeline,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["opportunities"] }),
        queryClient.invalidateQueries({ queryKey: ["products"] }),
        queryClient.invalidateQueries({ queryKey: ["plugin-runs"] })
      ]);
    }
  });

  return (
    <div className="flex flex-wrap items-center gap-3">
      <button
        type="button"
        onClick={() => mutation.mutate()}
        disabled={mutation.isPending}
        className="inline-flex h-10 items-center gap-2 border border-terminal-green/70 bg-terminal-green/10 px-3 text-sm font-medium text-terminal-green transition hover:bg-terminal-green/15 disabled:cursor-wait disabled:opacity-60"
      >
        {mutation.isPending ? <RefreshCw size={16} className="animate-spin" /> : <Play size={16} />}
        <span>{mutation.isPending ? "Running" : "Run Pipeline"}</span>
      </button>
      {mutation.data ? (
        <span className="font-mono text-xs text-terminal-muted">
          {mutation.data.status} / {mutation.data.observations_created} obs /{" "}
          {mutation.data.products_updated} products
        </span>
      ) : null}
      {mutation.error ? (
        <span className="max-w-md truncate font-mono text-xs text-terminal-rose">
          {(mutation.error as Error).message}
        </span>
      ) : null}
    </div>
  );
}

