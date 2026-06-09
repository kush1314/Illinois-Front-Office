"use client";

import { useEffect, useState } from "react";
import { SectionCard } from "@/components/section-card";
import { Player, apiGet } from "@/lib/api";

type PlayersResponse = { items: Player[] };

type ScoutingReport = {
  player_name: string;
  executive_summary: string;
  strengths: string;
  weaknesses: string;
  projected_role: string;
  development_areas: string;
  illinois_fit: string;
  recruiting_recommendation: string;
  coach_notes: string;
};

const TIER_COLORS: Record<string, string> = {
  "TIER 1": "bg-green-50 border-green-300 text-green-800",
  "TIER 2": "bg-blue-50 border-blue-300 text-blue-800",
  "TIER 3": "bg-yellow-50 border-yellow-300 text-yellow-800",
  "AVOID":  "bg-red-50 border-red-300 text-red-700",
};

function ReportSection({ label, content }: { label: string; content: string }) {
  return (
    <div className="rounded-lg bg-slate-50 p-4">
      <p className="mb-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-400">{label}</p>
      <p className="text-sm leading-relaxed text-slate-700 whitespace-pre-line">{content}</p>
    </div>
  );
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api";

export default function ScoutingCenterPage(): JSX.Element {
  const [players, setPlayers] = useState<Player[]>([]);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState("");
  const [report, setReport] = useState<ScoutingReport | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    apiGet<PlayersResponse>("/players?limit=200").then((res) => {
      setPlayers(res.items);
      if (res.items.length > 0) setSelected(res.items[0].player_name);
    });
  }, []);

  useEffect(() => {
    if (!selected) return;
    setLoading(true);
    setReport(null);
    apiGet<ScoutingReport>(`/scouting/${encodeURIComponent(selected)}`)
      .then(setReport)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [selected]);

  const filtered = search
    ? players.filter(p =>
        p.player_name.toLowerCase().includes(search.toLowerCase()) ||
        p.school.toLowerCase().includes(search.toLowerCase()))
    : players;

  const tierKey = report?.recruiting_recommendation?.split("—")[0].trim().split(" ").slice(0,2).join(" ") ?? "";
  const tierColor = Object.entries(TIER_COLORS).find(([k]) => report?.recruiting_recommendation?.startsWith(k))?.[1]
    ?? "bg-slate-50 border-slate-200 text-slate-700";

  return (
    <div className="space-y-6">
      <SectionCard
        title="Scouting Center"
        subtitle="Full player scouting reports in plain English — export to PDF for staff distribution."
      >
        <div className="flex flex-col gap-3 sm:flex-row">
          <input
            className="h-11 flex-1 rounded-lg border border-slate-300 px-3 text-sm outline-none focus:border-orange"
            placeholder="Search player or school…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
          <select
            className="h-11 w-full rounded-lg border border-slate-300 px-3 text-sm sm:w-72"
            value={selected}
            onChange={e => { setSelected(e.target.value); setSearch(""); }}
          >
            {filtered.map(p => (
              <option key={p.player_name} value={p.player_name}>
                {p.player_name} — {p.school} ({p.position})
              </option>
            ))}
          </select>
          <a
            href={`${API_BASE}/scouting/${encodeURIComponent(selected)}/pdf`}
            target="_blank"
            rel="noreferrer"
            className="inline-flex h-11 items-center justify-center rounded-lg bg-orange px-4 font-semibold text-white text-sm transition hover:bg-navy whitespace-nowrap"
          >
            Export PDF
          </a>
        </div>
      </SectionCard>

      {loading && (
        <div className="flex h-32 items-center justify-center rounded-xl border border-slate-200 bg-white">
          <p className="text-sm text-slate-400">Generating scouting report…</p>
        </div>
      )}

      {report && !loading && (
        <>
          {/* Recruiting tier banner */}
          <div className={`rounded-xl border-2 p-4 ${tierColor}`}>
            <p className="text-xs font-bold uppercase tracking-wider opacity-70">Staff Recommendation</p>
            <p className="mt-1 font-bold text-lg">{report.recruiting_recommendation}</p>
          </div>

          {/* Executive summary */}
          <SectionCard title="Player Overview" subtitle={report.player_name}>
            <p className="text-sm leading-relaxed text-slate-700 whitespace-pre-line">{report.executive_summary}</p>
          </SectionCard>

          <div className="grid gap-4 md:grid-cols-2">
            <SectionCard title="What He Brings" subtitle="Strengths that translate to Illinois">
              <ul className="space-y-2">
                {report.strengths.split("\n\n").filter(Boolean).map((s, i) => (
                  <li key={i} className="flex gap-2 text-sm text-slate-700">
                    <span className="mt-0.5 shrink-0 text-green-500 font-bold">+</span>
                    <span>{s}</span>
                  </li>
                ))}
              </ul>
            </SectionCard>

            <SectionCard title="Concerns" subtitle="What to validate before committing">
              <ul className="space-y-2">
                {report.weaknesses.split("\n\n").filter(Boolean).map((w, i) => (
                  <li key={i} className="flex gap-2 text-sm text-slate-700">
                    <span className="mt-0.5 shrink-0 text-red-400 font-bold">−</span>
                    <span>{w}</span>
                  </li>
                ))}
              </ul>
            </SectionCard>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <ReportSection label="Projected Role at Illinois" content={report.projected_role} />
            <ReportSection label="Development Priorities" content={report.development_areas} />
            <ReportSection label="Illinois System Fit" content={report.illinois_fit} />
          </div>

          <div className="rounded-xl border border-navy/20 bg-navy/5 p-4">
            <p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-navy">Coach Film Notes</p>
            <p className="text-sm leading-relaxed text-slate-700">{report.coach_notes}</p>
          </div>
        </>
      )}
    </div>
  );
}
