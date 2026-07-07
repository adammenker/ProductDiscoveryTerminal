import { dateTime, titleCase } from "@/lib/format";
import type { PluginRunSummary } from "@/types/api";

export function PluginRunTable({ runs }: { runs: PluginRunSummary[] }) {
  return (
    <div className="overflow-x-auto border border-terminal-line bg-terminal-bg">
      <table className="w-full min-w-[760px] border-collapse text-left text-sm">
        <thead className="bg-terminal-panel text-xs uppercase text-terminal-muted">
          <tr>
            <th className="border-b border-terminal-line px-3 py-2 font-mono font-medium">Plugin</th>
            <th className="border-b border-terminal-line px-3 py-2 font-mono font-medium">Type</th>
            <th className="border-b border-terminal-line px-3 py-2 font-mono font-medium">Status</th>
            <th className="border-b border-terminal-line px-3 py-2 font-mono font-medium">Created</th>
            <th className="border-b border-terminal-line px-3 py-2 font-mono font-medium">Skipped</th>
            <th className="border-b border-terminal-line px-3 py-2 font-mono font-medium">Started</th>
            <th className="border-b border-terminal-line px-3 py-2 font-mono font-medium">Error</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run, index) => (
            <tr key={run.id ?? `${run.plugin_name}-${index}`} className="border-b border-terminal-line/70">
              <td className="px-3 py-2 font-medium">{run.plugin_name}</td>
              <td className="px-3 py-2 text-terminal-muted">{titleCase(run.plugin_type)}</td>
              <td className="px-3 py-2">
                <span className={statusClass(run.status)}>{titleCase(run.status)}</span>
              </td>
              <td className="px-3 py-2 font-mono text-xs tabular-nums">{run.records_created}</td>
              <td className="px-3 py-2 font-mono text-xs tabular-nums">{run.records_updated}</td>
              <td className="px-3 py-2 font-mono text-xs text-terminal-muted">{dateTime(run.started_at)}</td>
              <td className="max-w-[260px] truncate px-3 py-2 text-xs text-terminal-rose">{run.error_message}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function statusClass(status: string) {
  if (status === "success") {
    return "inline-flex h-7 items-center border border-terminal-green/60 bg-terminal-green/10 px-2 font-mono text-xs text-terminal-green";
  }
  if (status === "failed") {
    return "inline-flex h-7 items-center border border-terminal-rose/60 bg-terminal-rose/10 px-2 font-mono text-xs text-terminal-rose";
  }
  return "inline-flex h-7 items-center border border-terminal-amber/60 bg-terminal-amber/10 px-2 font-mono text-xs text-terminal-amber";
}

