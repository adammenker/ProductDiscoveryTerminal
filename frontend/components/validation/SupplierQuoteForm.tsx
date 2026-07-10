"use client";

import { Loader2, Plus } from "lucide-react";
import { useState } from "react";
import { useCreateSupplierQuote } from "@/lib/validation-hooks";

const fieldClass =
  "h-9 w-full border border-terminal-line bg-terminal-bg px-2.5 text-sm outline-none placeholder:text-terminal-muted focus:border-terminal-green";

export function SupplierQuoteForm({ productId }: { productId: string }) {
  const createQuote = useCreateSupplierQuote(productId);
  const [form, setForm] = useState({
    supplier_name: "",
    supplier_url: "",
    unit_cost: "",
    freight_cost_per_unit: "",
    packaging_cost_per_unit: "",
    moq: "",
    lead_time_days: "",
    country: "",
    notes: ""
  });

  function update(key: keyof typeof form, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  return (
    <form
      className="space-y-3"
      onSubmit={(event) => {
        event.preventDefault();
        createQuote.mutate(
          {
            source: "manual",
            supplier_name: form.supplier_name || null,
            supplier_url: form.supplier_url || null,
            unit_cost: Number(form.unit_cost),
            freight_cost_per_unit: optionalNumber(form.freight_cost_per_unit),
            packaging_cost_per_unit: optionalNumber(form.packaging_cost_per_unit),
            moq: optionalNumber(form.moq),
            lead_time_days: optionalNumber(form.lead_time_days),
            country: form.country || null,
            currency: "USD",
            quote_status: "needs_review",
            confidence: 0.6,
            notes: form.notes || null
          },
          {
            onSuccess: () =>
              setForm({
                supplier_name: "",
                supplier_url: "",
                unit_cost: "",
                freight_cost_per_unit: "",
                packaging_cost_per_unit: "",
                moq: "",
                lead_time_days: "",
                country: "",
                notes: ""
              })
          }
        );
      }}
    >
      <div className="grid gap-2 sm:grid-cols-2">
        <Field label="Supplier name">
          <input className={fieldClass} value={form.supplier_name} onChange={(event) => update("supplier_name", event.target.value)} />
        </Field>
        <Field label="Supplier URL">
          <input className={fieldClass} type="url" value={form.supplier_url} onChange={(event) => update("supplier_url", event.target.value)} />
        </Field>
      </div>
      <div className="grid gap-2 sm:grid-cols-3">
        <Field label="Unit cost *">
          <input className={fieldClass} required min="0" step="0.01" inputMode="decimal" value={form.unit_cost} onChange={(event) => update("unit_cost", event.target.value)} />
        </Field>
        <Field label="Freight / unit">
          <input className={fieldClass} min="0" step="0.01" inputMode="decimal" value={form.freight_cost_per_unit} onChange={(event) => update("freight_cost_per_unit", event.target.value)} />
        </Field>
        <Field label="Packaging / unit">
          <input className={fieldClass} min="0" step="0.01" inputMode="decimal" value={form.packaging_cost_per_unit} onChange={(event) => update("packaging_cost_per_unit", event.target.value)} />
        </Field>
      </div>
      <div className="grid gap-2 sm:grid-cols-3">
        <Field label="MOQ">
          <input className={fieldClass} min="1" step="1" inputMode="numeric" value={form.moq} onChange={(event) => update("moq", event.target.value)} />
        </Field>
        <Field label="Lead time days">
          <input className={fieldClass} min="0" step="1" inputMode="numeric" value={form.lead_time_days} onChange={(event) => update("lead_time_days", event.target.value)} />
        </Field>
        <Field label="Country">
          <input className={fieldClass} value={form.country} onChange={(event) => update("country", event.target.value)} />
        </Field>
      </div>
      <Field label="Notes">
        <textarea
          className="min-h-20 w-full resize-y border border-terminal-line bg-terminal-bg px-2.5 py-2 text-sm outline-none focus:border-terminal-green"
          value={form.notes}
          onChange={(event) => update("notes", event.target.value)}
        />
      </Field>
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="submit"
          disabled={createQuote.isPending || !form.unit_cost}
          className="inline-flex h-9 items-center gap-2 border border-terminal-green/60 bg-terminal-green/10 px-3 text-sm text-terminal-green disabled:cursor-not-allowed disabled:opacity-50"
        >
          {createQuote.isPending ? <Loader2 size={15} className="animate-spin" /> : <Plus size={15} />}
          Add quote
        </button>
        {createQuote.error ? <span className="text-xs text-terminal-rose">{createQuote.error.message}</span> : null}
        {createQuote.isSuccess ? <span className="text-xs text-terminal-green">Quote recorded.</span> : null}
      </div>
    </form>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block font-mono text-[11px] uppercase text-terminal-muted">{label}</span>
      {children}
    </label>
  );
}

function optionalNumber(value: string) {
  return value === "" ? null : Number(value);
}
