export function EmptyState({ label }: { label: string }) {
  return (
    <div className="border border-dashed border-terminal-line bg-terminal-panel/70 p-6 text-sm text-terminal-muted">
      {label}
    </div>
  );
}

