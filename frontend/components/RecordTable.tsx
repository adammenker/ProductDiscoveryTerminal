type RecordRow = Record<string, unknown>;

export function RecordTable({ rows, columns }: { rows: RecordRow[]; columns: string[] }) {
  return (
    <div className="overflow-x-auto border border-terminal-line bg-terminal-bg">
      <table className="w-full min-w-[680px] border-collapse text-left text-sm">
        <thead className="bg-terminal-panel text-xs uppercase text-terminal-muted">
          <tr>
            {columns.map((column) => (
              <th key={column} className="border-b border-terminal-line px-3 py-2 font-mono font-medium">
                {column.replace(/_/g, " ")}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={String(row.id ?? index)} className="border-b border-terminal-line/70">
              {columns.map((column) => (
                <td key={column} className="max-w-[360px] truncate px-3 py-2 text-terminal-muted">
                  {displayValue(row[column])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function displayValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "--";
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(2);
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value.join(", ");
  return JSON.stringify(value);
}

