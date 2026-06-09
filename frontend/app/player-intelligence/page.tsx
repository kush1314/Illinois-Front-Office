"use client";

import { useEffect, useState } from "react";
import Plot from "@/components/plot";
import { SectionCard } from "@/components/section-card";
import { Player, apiGet, formatPct } from "@/lib/api";

type Comp = {
  player_name: string;
  school: string;
  position: string;
  transfer_success_score: number;
  similarity: number;
};

type PlayerIntelligenceResponse = {
  player: Player & Record<string, unknown>;
  radar: Record<string, number>;
  archetype: string;
  comparable_players: Comp[];
  strengths: string[];
  weaknesses: string[];
  ai_scouting_report: string;
};

type PlayersResponse = { items: Player[] };

function StatRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex items-center justify-between border-b border-slate-100 py-2 last:border-0">
      <span className="text-xs text-slate-500">{label}</span>
      <span className="text-sm font-semibold text-navy">{value}</span>
    </div>
  );
}

export default function PlayerIntelligencePage(): JSX.Element {
  const [players, setPlayers] = useState<Player[]>([]);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState("");
  const [details, setDetails] = useState<PlayerIntelligenceResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    apiGet<PlayersResponse>("/players?limit=150").then((res) => {
      setPlayers(res.items);
      if (res.items.length > 0) setSelected(res.items[0].player_name);
    });
  }, []);

  useEffect(() => {
    if (!selected) return;
    setLoading(true);
    setDetails(null);
    apiGet<PlayerIntelligenceResponse>(`/player/${encodeURIComponent(selected)}`)
      .then(setDetails)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [selected]);

  const filtered = search
    ? players.filter((p) => p.player_name.toLowerCase().includes(search.toLowerCase()) || p.school.toLowerCase().includes(search.toLowerCase()))
    : players;

  const radarLabels = Object.keys(details?.radar ?? {});
  const radarValues = Object.values(details?.radar ?? {});

  const p = details?.player;

  return (
    <div className="space-y-6">
      <SectionCard title="Player Intelligence" subtitle="Deep individual analysis: prediction score, radar profile, comps, strengths, and fit verdict.">
        <div className="flex flex-col gap-3 sm:flex-row">
          <input
            className="h-11 flex-1 rounded-lg border border-slate-300 px-3 text-sm outline-none focus:border-orange focus:ring-1 focus:ring-orange/30"
            placeholder="Search any player or school…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <select
            className="h-11 w-full rounded-lg border border-slate-300 px-3 text-sm sm:w-72"
            value={selected}
            onChange={(e) => { setSelected(e.target.value); setSearch(""); }}
          >
            {filtered.map((pl) => (
              <option key={pl.player_name} value={pl.player_name}>
                {pl.player_name} — {pl.school} ({pl.position})
              </option>
            ))}
          </select>
        </div>
      </SectionCard>

      {loading && (
        <div className="flex h-32 items-center justify-center rounded-xl border border-slate-200 bg-white">
          <p className="text-sm text-slate-400">Loading player profile…</p>
        </div>
      )}

      {details && !loading && (
        <>
          {/* Header card */}
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex flex-wrap items-start gap-4">
              <div className="flex h-16 w-16 items-center justify-center rounded-xl bg-navy text-xl font-extrabold text-white">
                {details.player.player_name.split(" ").map((n) => n[0]).join("").slice(0, 2)}
              </div>
              <div className="flex-1">
                <h2 className="text-xl font-extrabold text-navy">{details.player.player_name}</h2>
                <p className="text-sm text-slate-500">{details.player.school} · {details.player.position} · {details.player.conference}</p>
                <span className="mt-1 inline-block rounded-full bg-orange/15 px-3 py-0.5 text-[11px] font-semibold text-orange">
                  {details.archetype}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-3 text-center md:grid-cols-4">
                {[
                  { l: "Likely to Succeed", v: `${p?.transfer_success_score?.toFixed(0)}%`, good: (p?.transfer_success_score ?? 0) >= 60 },
                  { l: "Illinois Fit", v: `${p?.illinois_fit_score?.toFixed(0) ?? "—"}/100`, good: (p?.illinois_fit_score ?? 0) >= 55 },
                  { l: "Risk (lower=safer)", v: `${p?.risk_score?.toFixed(0) ?? "—"}/100`, good: (p?.risk_score ?? 100) < 40 },
                  { l: "Hidden Gem", v: `${p?.hidden_gem_score?.toFixed(0) ?? "—"}/100`, good: (p?.hidden_gem_score ?? 0) >= 35 },
                ].map((s) => (
                  <div key={s.l} className="rounded-lg border border-slate-200 px-3 py-2">
                    <p className="text-[10px] uppercase text-slate-400">{s.l}</p>
                    <p className={`text-lg font-extrabold ${s.good ? "text-green-600" : "text-red-500"}`}>{s.v}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            {/* Radar */}
            <SectionCard title="Skill Radar" subtitle="Shooting · Playmaking · Defense · Rebounding · Efficiency · Fit">
              <Plot
                data={[{
                  type: "scatterpolar",
                  theta: [...radarLabels, radarLabels[0]],
                  r: [...radarValues, radarValues[0]],
                  fill: "toself",
                  line: { color: "#FF5F05" },
                  fillcolor: "rgba(255,95,5,0.18)",
                  name: details.player.player_name,
                }]}
                layout={{
                  autosize: true,
                  paper_bgcolor: "rgba(0,0,0,0)",
                  polar: { radialaxis: { visible: true, range: [0, 100], tickfont: { size: 9 } } },
                  margin: { t: 20, l: 20, r: 20, b: 20 },
                  height: 320,
                }}
                style={{ width: "100%", height: 320 }}
                config={{ displayModeBar: false }}
              />
            </SectionCard>

            {/* Stats */}
            <SectionCard title="Statistical Profile" subtitle="Key production metrics">
              <StatRow label="True Shooting %" value={formatPct(p?.ts_pct as number ?? 0)} />
              <StatRow label="3-Point %" value={formatPct(p?.three_pt_pct as number ?? 0)} />
              <StatRow label="Assist Rate" value={`${(p?.assist_rate as number ?? 0)?.toFixed(1)}%`} />
              <StatRow label="Turnover Rate" value={`${(p?.turnover_rate as number ?? 0)?.toFixed(1)}%`} />
              <StatRow label="Steal Rate" value={`${(p?.steal_rate as number ?? 0)?.toFixed(1)}%`} />
              <StatRow label="Block Rate" value={`${(p?.block_rate as number ?? 0)?.toFixed(1)}%`} />
              <StatRow label="Def Rebound Rate" value={`${(p?.def_rebound_rate as number ?? 0)?.toFixed(1)}%`} />
              <StatRow label="Defensive Rating" value={(p?.defensive_rating as number ?? 0)?.toFixed(0)} />
              <StatRow label="Offensive Rating" value={(p?.offensive_rating as number ?? 0)?.toFixed(0)} />
              <StatRow label="Usage Rate" value={`${(p?.usage_rate as number ?? 0)?.toFixed(1)}%`} />
              <StatRow label="Minutes" value={(p?.minutes as number ?? 0)?.toFixed(0)} />
            </SectionCard>
          </div>

          {/* Strengths & Weaknesses */}
          <div className="grid gap-4 xl:grid-cols-2">
            <SectionCard title="Strengths" subtitle="What translates well at the Big Ten level">
              <ul className="space-y-2">
                {details.strengths.map((item) => (
                  <li key={item} className="flex items-start gap-2 text-sm text-slate-700">
                    <span className="mt-0.5 text-green-500 text-base leading-none">+</span>
                    {item}
                  </li>
                ))}
              </ul>
            </SectionCard>
            <SectionCard title="Concerns" subtitle="Risk areas and development needs">
              <ul className="space-y-2">
                {details.weaknesses.map((item) => (
                  <li key={item} className="flex items-start gap-2 text-sm text-slate-700">
                    <span className="mt-0.5 text-red-400 text-base leading-none">–</span>
                    {item}
                  </li>
                ))}
              </ul>
            </SectionCard>
          </div>

          {/* Comparable players */}
          <SectionCard title="Comparable Players" subtitle="Closest statistical profiles in the portal database (cosine similarity)">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100 text-xs text-slate-400">
                    <th className="pb-2 text-left font-semibold">Player</th>
                    <th className="pb-2 text-left font-semibold">School</th>
                    <th className="pb-2 text-center font-semibold">Pos</th>
                    <th className="pb-2 text-right font-semibold">Success Score</th>
                    <th className="pb-2 text-right font-semibold">Similarity</th>
                  </tr>
                </thead>
                <tbody>
                  {(details.comparable_players as Comp[]).map((c) => (
                    <tr key={c.player_name} className="border-b border-slate-50 hover:bg-slate-50">
                      <td className="py-2 font-medium text-navy">{c.player_name}</td>
                      <td className="py-2 text-slate-500">{c.school}</td>
                      <td className="py-2 text-center text-slate-500">{c.position}</td>
                      <td className="py-2 text-right font-semibold">{c.transfer_success_score?.toFixed(1)}%</td>
                      <td className="py-2 text-right text-slate-500">{(c.similarity * 100).toFixed(0)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </SectionCard>

          {/* Scouting Report */}
          <SectionCard
            title="Front Office Summary"
            subtitle="Based on 2024-25 BartTorvik stats and the scoring model"
          >
            <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700">{details.ai_scouting_report}</p>
            <div className="mt-3 flex gap-2">
              <a
                href={`/scouting-center?focused=1`}
                className="rounded-lg border border-orange px-3 py-1.5 text-xs font-semibold text-orange transition hover:bg-orange hover:text-white"
              >
                Full Scouting Report →
              </a>
            </div>
          </SectionCard>
        </>
      )}
    </div>
  );
}
