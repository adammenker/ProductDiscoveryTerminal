"use client";

import { Camera, Loader2 } from "lucide-react";
import { useState } from "react";
import { useCreateSnapshot } from "@/lib/validation-hooks";
import type { PaperDecision } from "@/types/api";

export function SnapshotControl({ productId }: { productId: string }) {
  const createSnapshot = useCreateSnapshot(productId);
  const [decision, setDecision] = useState<PaperDecision>("paper_watch");
  const [hypothesis, setHypothesis] = useState("");

  return (
    <form
      className="grid gap-3 md:grid-cols-[180px_1fr_auto]"
      onSubmit={(event) => {
        event.preventDefault();
        createSnapshot.mutate({
          snapshot_reason: "manual_validation",
          decision,
          hypothesis: hypothesis || null
        });
      }}
    >
      <label>
        <span className="mb-1 block font-mono text-[11px] uppercase text-terminal-muted">Paper decision</span>
        <select
          value={decision}
          onChange={(event) => setDecision(event.target.value as PaperDecision)}
          className="h-9 w-full border border-terminal-line bg-terminal-bg px-2 text-sm outline-none focus:border-terminal-green"
        >
          <option value="paper_pursue">Paper pursue</option>
          <option value="paper_watch">Paper watch</option>
          <option value="paper_skip">Paper skip</option>
        </select>
      </label>
      <label>
        <span className="mb-1 block font-mono text-[11px] uppercase text-terminal-muted">Hypothesis</span>
        <input
          value={hypothesis}
          onChange={(event) => setHypothesis(event.target.value)}
          placeholder="What should be true at evaluation?"
          className="h-9 w-full border border-terminal-line bg-terminal-bg px-2.5 text-sm outline-none placeholder:text-terminal-muted focus:border-terminal-green"
        />
      </label>
      <button
        type="submit"
        disabled={createSnapshot.isPending}
        className="mt-5 inline-flex h-9 items-center justify-center gap-2 border border-terminal-cyan/60 bg-terminal-cyan/10 px-3 text-sm text-terminal-cyan disabled:opacity-50"
      >
        {createSnapshot.isPending ? <Loader2 size={15} className="animate-spin" /> : <Camera size={15} />}
        Snapshot
      </button>
      <div className="md:col-span-3">
        {createSnapshot.error ? <span className="text-xs text-terminal-rose">{createSnapshot.error.message}</span> : null}
        {createSnapshot.data ? (
          <span className="text-xs text-terminal-green">
            Snapshot created{createSnapshot.data.paper_trade ? " with an open paper trade" : ""}.
          </span>
        ) : null}
      </div>
    </form>
  );
}
