import type { Recommendation } from "@/types/api";

export function formatScore(value: number | null | undefined) {
  if (value === null || value === undefined) return "--";
  return value.toFixed(1);
}

export function titleCase(value: string | null | undefined) {
  if (!value) return "Uncategorized";
  return value
    .replace(/_/g, " ")
    .split(" ")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function recommendationLabel(value: Recommendation | string | null | undefined) {
  if (!value) return "No Score";
  return titleCase(value);
}

export function dateTime(value: string | null | undefined) {
  if (!value) return "--";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit"
  }).format(new Date(value));
}

export function currency(value: number | string | null | undefined, code = "USD") {
  if (value === null || value === undefined || value === "") return "--";
  const number = typeof value === "number" ? value : Number(value);
  if (Number.isNaN(number)) return "--";
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: code,
    maximumFractionDigits: 2
  }).format(number);
}

export function percent(value: number | string | null | undefined) {
  if (value === null || value === undefined || value === "") return "--";
  const number = typeof value === "number" ? value : Number(value);
  if (Number.isNaN(number)) return "--";
  return `${number.toFixed(1)}%`;
}
