import type { ProductListItem } from "@/types/api";

export type SortDirection = "asc" | "desc";

export type ProductSortKey =
  | "product"
  | "category"
  | "score"
  | "eligible"
  | "decision"
  | "validation"
  | "economics"
  | "supplier"
  | "evidence"
  | "missing"
  | "recommendation"
  | "updated";

export type ProductSortState = {
  key: ProductSortKey;
  direction: SortDirection;
} | null;

export function nextProductSort(
  current: ProductSortState,
  key: ProductSortKey
): ProductSortState {
  if (current?.key === key) {
    return { key, direction: current.direction === "asc" ? "desc" : "asc" };
  }
  return { key, direction: defaultDirection(key) };
}

export function sortProducts(products: ProductListItem[], sort: ProductSortState) {
  if (!sort) return products;
  return products
    .map((product, index) => ({ product, index }))
    .sort((left, right) => {
      const leftValue = productSortValue(left.product, sort.key);
      const rightValue = productSortValue(right.product, sort.key);
      const leftMissing = isMissing(leftValue);
      const rightMissing = isMissing(rightValue);
      if (leftMissing && rightMissing) return left.index - right.index;
      if (leftMissing) return 1;
      if (rightMissing) return -1;
      const comparison = compareValues(leftValue, rightValue);
      if (comparison === 0) return left.index - right.index;
      return sort.direction === "asc" ? comparison : -comparison;
    })
    .map((row) => row.product);
}

function productSortValue(product: ProductListItem, key: ProductSortKey) {
  switch (key) {
    case "product":
      return product.canonical_name;
    case "category":
      return product.category;
    case "score":
      return product.latest_score ?? product.opportunity_score;
    case "eligible":
      return product.constraint_eligible;
    case "decision":
      return product.validation_decision ?? product.recommendation;
    case "validation":
      return product.validation_decision;
    case "economics":
      return product.economics_decision;
    case "supplier":
      return product.supplier_validation_decision;
    case "evidence":
      return product.cross_source_confidence_score;
    case "missing":
      return product.missing_evidence.length;
    case "recommendation":
      return product.recommendation;
    case "updated":
      return Date.parse(product.updated_at);
  }
}

function compareValues(
  left: string | number | boolean | null | undefined,
  right: string | number | boolean | null | undefined
) {
  if (typeof left === "number" && typeof right === "number") return left - right;
  if (typeof left === "boolean" && typeof right === "boolean") {
    return Number(left) - Number(right);
  }
  return String(left).localeCompare(String(right), undefined, {
    numeric: true,
    sensitivity: "base"
  });
}

function defaultDirection(key: ProductSortKey): SortDirection {
  if (["score", "evidence", "missing", "updated"].includes(key)) return "desc";
  return "asc";
}

function isMissing(value: string | number | boolean | null | undefined) {
  return value === null || value === undefined || value === "";
}
