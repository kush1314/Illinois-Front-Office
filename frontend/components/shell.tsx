"use client";

import { ReactNode, Suspense } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, ChevronRight } from "lucide-react";

import { Sidebar } from "@/components/sidebar";

const PAGE_TITLES: Record<string, string> = {
  "/recruiting-center":         "Recruiting Center",
  "/player-intelligence":       "Player Intelligence",
  "/hidden-gem-lab":            "Hidden Gem Lab",
  "/transfer-success-predictor":"Transfer Success Predictor",
  "/compare-players":           "Compare Players",
  "/front-office-insights":     "Front Office Insights",
  "/roster-builder":            "Roster Builder",
  "/scouting-center":           "Scouting Center",
  "/methodology":               "Methodology & Data",
  "/glossary":                  "Metric Glossary",
};

function ShellInner({ children }: { children: ReactNode }): JSX.Element {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const isHome = pathname === "/";
  const isFocused = searchParams.get("focused") === "1";

  // Home page: no shell wrapper
  if (isHome) {
    return (
      <div className="min-h-screen bg-bg text-text">
        <main>{children}</main>
      </div>
    );
  }

  // Focused mode: came from an agent chat link → no sidebar, only Back to Agents
  if (isFocused) {
    const pageTitle = PAGE_TITLES[pathname] ?? "View";
    return (
      <div className="min-h-screen bg-bg text-text">
        {/* Minimal focused header — back button only, no cross-navigation */}
        <div className="sticky top-0 z-40 flex items-center gap-3 border-b border-slate-200 bg-white px-4 py-2.5 shadow-sm">
          <Link
            href="/"
            className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-navy transition hover:bg-navy hover:text-white"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Illinois Front Office
          </Link>
          <ChevronRight className="h-3.5 w-3.5 text-slate-300" />
          <span className="text-sm font-semibold text-navy">{pageTitle}</span>
        </div>
        <main className="p-5 md:p-8">{children}</main>
      </div>
    );
  }

  // Normal mode: sidebar + full layout
  return (
    <div className="min-h-screen bg-bg text-text md:flex">
      <Sidebar />
      <main className="flex-1 p-5 md:p-8">{children}</main>
    </div>
  );
}

export function Shell({ children }: { children: ReactNode }): JSX.Element {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-bg text-text md:flex">
          <main className="flex-1 p-5 md:p-8">{children}</main>
        </div>
      }
    >
      <ShellInner>{children}</ShellInner>
    </Suspense>
  );
}
