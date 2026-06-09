"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  ["/", "Home"],
  ["/recruiting-center", "Recruiting Center"],
  ["/player-intelligence", "Player Intelligence"],
  ["/hidden-gem-lab", "Hidden Gem Lab"],
  ["/transfer-success-predictor", "Transfer Success Predictor"],
  ["/compare-players", "Compare Players"],
  ["/roster-builder", "Roster Builder"],
  ["/scouting-center", "Scouting Center"],
  ["/front-office-insights", "Front Office Insights"],
  ["/methodology", "Methodology & Data"],
  ["/glossary", "Metric Glossary"],
];

export function Sidebar(): JSX.Element {
  const pathname = usePathname();

  return (
    <aside className="w-full shrink-0 bg-navy px-5 py-6 text-white md:min-h-screen md:w-72">
      <p className="text-xs uppercase tracking-[0.22em] text-white/70">Illinois Front Office</p>
      <h1 className="mt-2 text-2xl font-bold leading-tight">Basketball Operations Platform</h1>
      <p className="mt-3 text-sm text-white/75">Recruiting, scouting, roster construction, and transfer analytics.</p>

      <nav className="mt-8 flex flex-col gap-2">
        {links.map(([href, label]) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={`rounded-lg px-3 py-2 text-sm font-medium transition ${
                active ? "bg-orange text-white shadow" : "text-white/80 hover:bg-white/10 hover:text-white"
              }`}
            >
              {label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
