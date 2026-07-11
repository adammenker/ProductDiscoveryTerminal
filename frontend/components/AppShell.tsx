"use client";

import clsx from "clsx";
import {
  ChartNoAxesCombined,
  Gauge,
  History,
  ListChecks,
  PackageSearch,
  PlugZap,
  TerminalSquare
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/", label: "Dashboard", icon: Gauge },
  { href: "/validator", label: "Validator", icon: ListChecks },
  { href: "/products", label: "Products", icon: PackageSearch },
  { href: "/backtests", label: "Backtests", icon: ChartNoAxesCombined },
  { href: "/plugins", label: "Plugins", icon: PlugZap },
  { href: "/runs", label: "Runs", icon: History }
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-terminal-bg text-terminal-ink terminal-grid">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-64 border-r border-terminal-line bg-terminal-bg/95 px-4 py-5 backdrop-blur md:block">
        <Link href="/" className="flex h-10 items-center gap-3 font-mono text-sm uppercase tracking-[0.24em]">
          <span className="flex h-9 w-9 items-center justify-center border border-terminal-green/50 bg-terminal-green/10 text-terminal-green">
            <TerminalSquare size={18} />
          </span>
          <span>PDT</span>
        </Link>
        <nav className="mt-8 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={clsx(
                  "flex h-10 items-center gap-3 border px-3 text-sm transition",
                  active
                    ? "border-terminal-green/60 bg-terminal-green/10 text-terminal-green"
                    : "border-transparent text-terminal-muted hover:border-terminal-line hover:bg-terminal-panel hover:text-terminal-ink"
                )}
              >
                <Icon size={16} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
        <div className="absolute bottom-5 left-4 right-4 border border-terminal-line bg-terminal-panel/80 p-3 font-mono text-xs text-terminal-muted">
          <div className="text-terminal-green">recommendation_v2</div>
          <div className="mt-1">evidence aware</div>
        </div>
      </aside>

      <div className="md:pl-64">
        <header className="sticky top-0 z-10 border-b border-terminal-line bg-terminal-bg/90 px-4 py-3 backdrop-blur md:hidden">
          <div className="flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2 font-mono text-sm uppercase tracking-[0.2em]">
              <TerminalSquare size={18} className="text-terminal-green" />
              PDT
            </Link>
            <nav className="flex max-w-[250px] items-center gap-2 overflow-x-auto">
              {navItems.map((item) => {
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    title={item.label}
                    className="flex h-8 w-8 items-center justify-center border border-terminal-line bg-terminal-panel text-terminal-muted"
                  >
                    <Icon size={15} />
                  </Link>
                );
              })}
            </nav>
          </div>
        </header>
        <main className="mx-auto min-h-screen max-w-7xl px-4 py-6 sm:px-6 lg:px-8">{children}</main>
      </div>
    </div>
  );
}
