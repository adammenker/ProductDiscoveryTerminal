"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowRight, ClipboardCheck } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { api } from "@/lib/api";

export default function ValidationsPage() {
  const [status, setStatus] = useState("");
  const query = useQuery({ queryKey: ["validation-projects", status], queryFn: () => api.validationProjects(status || undefined) });
  const rows = query.data ?? [];
  return <div className="space-y-6">
    <header className="flex flex-col gap-3 border-b border-terminal-line pb-5 sm:flex-row sm:items-end sm:justify-between">
      <div><div className="mb-2 flex items-center gap-2 font-mono text-xs uppercase text-terminal-green"><ClipboardCheck size={15} /> Validation queue</div><h1 className="text-2xl font-semibold">Product validation projects</h1><p className="mt-2 text-sm text-terminal-muted">Move ranked opportunities from marketplace evidence to a documented sample decision.</p></div>
      <select value={status} onChange={(e) => setStatus(e.target.value)} className="h-10 border border-terminal-line bg-terminal-panel px-3 text-sm"><option value="">All statuses</option>{["draft","marketplace_validation","sourcing","ready_for_decision","approved_for_sample","rejected","archived"].map(value => <option key={value}>{value}</option>)}</select>
    </header>
    {query.isLoading ? <p className="text-sm text-terminal-muted">Loading validation queue...</p> : rows.length === 0 ? <div className="border border-terminal-line p-8 text-sm text-terminal-muted">No validation projects yet. Start one from a scored product.</div> :
      <div className="overflow-x-auto border border-terminal-line"><table className="w-full min-w-[920px] text-left text-sm"><thead className="bg-terminal-panel font-mono text-xs uppercase text-terminal-muted"><tr>{["Product","Status","Opportunity","Confidence","Max landed","Quotes","Best landed","Decision","Updated",""] .map(x => <th key={x} className="px-3 py-3 font-normal">{x}</th>)}</tr></thead><tbody>{rows.map(row => <tr key={row.id} className="border-t border-terminal-line"><td className="px-3 py-3 font-medium">{row.product_name}<div className="text-xs text-terminal-muted">{row.category ?? "Uncategorized"}</div></td><td className="px-3 py-3">{label(row.status)}</td><td className="px-3 py-3">{number(row.latest_opportunity_score)}</td><td className="px-3 py-3">{number(row.confidence_score)}</td><td className="px-3 py-3">{money(row.max_landed_cost)}</td><td className="px-3 py-3">{row.quote_count}</td><td className="px-3 py-3">{money(row.best_landed_cost)}</td><td className="px-3 py-3">{label(row.decision_readiness)}</td><td className="px-3 py-3 text-terminal-muted">{new Date(row.updated_at).toLocaleDateString()}</td><td className="px-3 py-3"><Link href={`/validations/${row.id}`} title="Open validation" className="inline-flex h-8 w-8 items-center justify-center border border-terminal-line text-terminal-green"><ArrowRight size={15} /></Link></td></tr>)}</tbody></table></div>}
  </div>;
}

const label = (value: string) => value.replaceAll("_", " ");
const number = (value: number | null) => value == null ? "—" : value.toFixed(1);
const money = (value: number | null) => value == null ? "—" : `$${value.toFixed(2)}`;
