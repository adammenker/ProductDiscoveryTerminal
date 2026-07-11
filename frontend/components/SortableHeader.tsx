import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import type { ProductSortKey, ProductSortState } from "@/lib/product-sort";

type SortableHeaderProps = {
  label: string;
  sortKey: ProductSortKey;
  sort: ProductSortState;
  onSort: (key: ProductSortKey) => void;
  className?: string;
  align?: "left" | "right";
};

export function SortableHeader({
  label,
  sortKey,
  sort,
  onSort,
  className = "",
  align = "left"
}: SortableHeaderProps) {
  const active = sort?.key === sortKey;
  const Icon = active ? (sort.direction === "asc" ? ArrowUp : ArrowDown) : ArrowUpDown;
  return (
    <th
      aria-sort={
        active ? (sort.direction === "asc" ? "ascending" : "descending") : "none"
      }
      className={`border-b border-terminal-line px-3 py-2 font-mono font-medium ${className}`}
    >
      <button
        type="button"
        onClick={() => onSort(sortKey)}
        className={`flex w-full items-center gap-1.5 hover:text-terminal-green ${
          align === "right" ? "justify-end text-right" : "justify-start text-left"
        }`}
      >
        <span>{label}</span>
        <Icon size={12} className={active ? "text-terminal-green" : "text-terminal-muted"} />
      </button>
    </th>
  );
}
