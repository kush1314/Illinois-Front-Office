"use client";

import { useEffect, useMemo, useState } from "react";
import { SectionCard } from "@/components/section-card";
import { Player, apiGet, apiPost, formatPct } from "@/lib/api";

type RosterResponse = {
  selected_players: Player[];
  roster_analysis: {
    // Real basketball stats
    projected_ppg:    number;
    projected_rpg:    number;
    projected_apg:    number;
    projected_orpg:   number;
    projected_drpg:   number;
    projected_spg:    number;
    projected_bpg:    number;
    projected_topg:   number;
    team_3pt_pct:     number;
    team_ts_pct:      number;
    team_ortg:        number;
    team_drtg:        number;
    net_rating:       number;
    projected_wins:   number;
    // Labels
    team_identity:         string;
    team_identity_summary: string;
    // Internal
    roster_grade:          number;
    spacing_score:         number;
    defensive_score:       number;
    risk_score:            number;
  };
  strengths:  string[];
  weaknesses: string[];
};

type PlayersResponse = { items: Player[] };

const ILLINOIS_CONTEXT = {
  ppg: 78.2, rpg: 36.8, apg: 15.1, ortg: 112.4, drtg: 103.1, wins: 20,
};

function StatCard({
  label, value, unit = "", context, positive
}: {
  label: string; value: string | number; unit?: string;
  context?: string; positive?: boolean;
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">{label}</p>
      <p className={`mt-1 text-3xl font-extrabold ${positive === true ? "text-green-600" : positive === false ? "text-red-500" : "text-navy"}`}>
        {value}{unit}
      </p>
      {context && <p className="mt-1 text-xs text-slate-500 leading-tight">{context}</p>}
    </div>
  );
}

function ExplainBox({ title, children }: { title: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50">
      <button
        className="flex w-full items-center justify-between px-4 py-2.5 text-left text-sm font-semibold text-navy"
        onClick={() => setOpen(o => !o)}
      >
        {title}
        <span className="text-slate-400">{open ? "▲" : "▼"}</span>
      </button>
      {open && <div className="border-t border-slate-200 px-4 py-3 text-sm text-slate-600 leading-relaxed">{children}</div>}
    </div>
  );
}

export default function RosterBuilderPage(): JSX.Element {
  const [players, setPlayers] = useState<Player[]>([]);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [result, setResult] = useState<RosterResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    apiGet<PlayersResponse>("/players?limit=200").then((res) => {
      setPlayers(res.items);
    });
  }, []);

  useEffect(() => {
    if (selected.length === 0) { setResult(null); return; }
    setLoading(true);
    apiPost<RosterResponse>("/roster-builder", { selected_players: selected })
      .then(setResult)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [selected]);

  const filtered = search
    ? players.filter(p => p.player_name.toLowerCase().includes(search.toLowerCase()) || p.school.toLowerCase().includes(search.toLowerCase()))
    : players;

  const ra = result?.roster_analysis;

  const ppgVsIllinois = ra ? ra.projected_ppg - ILLINOIS_CONTEXT.ppg : 0;
  const rpgVsIllinois = ra ? ra.projected_rpg - ILLINOIS_CONTEXT.rpg : 0;
  const ortgVsIllinois = ra ? ra.team_ortg - ILLINOIS_CONTEXT.ortg : 0;
  const drtgVsIllinois = ra ? ra.team_drtg - ILLINOIS_CONTEXT.drtg : 0;

  return (
    <div className="space-y-6">
      <SectionCard
        title="Hypothetical Roster Builder"
        subtitle="Pick any players, see what that team would look like statistically. All projections explained in plain English."
      >
        <div className="mb-3 rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800">
          <strong>How to use:</strong> Search for players below and click to add them to your hypothetical roster.
          You can add transfer targets, current players, or mix both.
          The stats update instantly every time you change the roster.
        </div>
        <div className="flex flex-col gap-3 sm:flex-row">
          <input
            className="h-10 flex-1 rounded-lg border border-slate-300 px-3 text-sm outline-none focus:border-orange focus:ring-1 focus:ring-orange/30"
            placeholder="Search any player or school to add to your lineup…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
          {selected.length > 0 && (
            <button
              onClick={() => setSelected([])}
              className="h-10 rounded-lg border border-red-200 bg-red-50 px-4 text-sm font-semibold text-red-600 transition hover:bg-red-100"
            >
              Clear All ({selected.length})
            </button>
          )}
        </div>

        {/* Player grid */}
        <div className="mt-3 grid gap-1.5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {filtered.slice(0, 60).map(p => {
            const active = selected.includes(p.player_name);
            return (
              <button
                key={p.player_name}
                className={`rounded-lg border px-3 py-2 text-left text-sm transition ${
                  active
                    ? "border-orange bg-orange/10 ring-1 ring-orange/40"
                    : "border-slate-200 bg-white hover:border-orange/40 hover:bg-orange/5"
                }`}
                onClick={() => setSelected(prev =>
                  prev.includes(p.player_name)
                    ? prev.filter(n => n !== p.player_name)
                    : [...prev, p.player_name].slice(0, 12)
                )}
              >
                <p className="font-semibold text-navy truncate">{p.player_name}</p>
                <p className="text-xs text-slate-500">{p.position} · {p.school} · {p.ppg?.toFixed(1)} PPG</p>
              </button>
            );
          })}
        </div>
        {search && <p className="mt-1 text-xs text-slate-400">{filtered.length} results — showing first 60</p>}
      </SectionCard>

      {/* Selected players */}
      {selected.length > 0 && (
        <SectionCard title={`Your Lineup (${selected.length} players)`} subtitle="Click a name to remove">
          <div className="flex flex-wrap gap-2">
            {selected.map(name => {
              const p = players.find(pl => pl.player_name === name);
              return (
                <button
                  key={name}
                  onClick={() => setSelected(prev => prev.filter(n => n !== name))}
                  className="flex items-center gap-2 rounded-full border border-orange/50 bg-orange/10 px-3 py-1.5 text-sm font-medium text-navy transition hover:bg-red-50 hover:border-red-300 hover:text-red-600"
                >
                  <span>{name}</span>
                  {p && <span className="text-xs text-slate-400">{p.position} · {p.school}</span>}
                  <span className="text-slate-400">×</span>
                </button>
              );
            })}
          </div>
        </SectionCard>
      )}

      {loading && (
        <div className="flex h-32 items-center justify-center rounded-xl border border-slate-200 bg-white">
          <p className="text-sm text-slate-400">Calculating projected stats…</p>
        </div>
      )}

      {result && ra && !loading && (
        <>
          {/* Team identity */}
          <div className="rounded-xl border border-navy/20 bg-navy p-5 text-white">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-widest text-white/60">Projected Team Identity</p>
                <h2 className="mt-1 text-2xl font-extrabold">{ra.team_identity}</h2>
                <p className="mt-1 text-sm text-white/70">{ra.team_identity_summary}</p>
              </div>
              <div className="text-right">
                <p className="text-xs text-white/60">Projected Season</p>
                <p className="text-3xl font-extrabold text-orange">{ra.projected_wins} wins</p>
                <p className="text-xs text-white/50">
                  Net rating {ra.net_rating > 0 ? "+" : ""}{ra.net_rating?.toFixed(1)} per 100 possessions
                </p>
              </div>
            </div>
          </div>

          {/* How wins were calculated */}
          <ExplainBox title="How were the projected wins calculated?">
            <p>
              Win projection is based on <strong>Net Rating</strong> — how many more points your team scores than it gives up per 100 possessions.
              Your projected Net Rating is <strong>{ra.net_rating > 0 ? "+" : ""}{ra.net_rating?.toFixed(1)}</strong>
              ({ra.team_ortg?.toFixed(1)} offensive efficiency minus {ra.team_drtg?.toFixed(1)} defensive efficiency).
            </p>
            <p className="mt-2">
              In college basketball, roughly every <strong>+1.5 Net Rating points ≈ 1 additional win</strong> over a season.
              An average Big Ten team runs about 0 Net Rating (~20 wins).
              Your lineup projects to <strong>{ra.projected_wins} wins</strong> based on this formula.
              Compare: the 2024-25 Illinois team had a Net Rating around +9.3.
            </p>
            <p className="mt-2 text-slate-400 text-xs">
              Note: this uses each player's individual Offensive Rating and Defensive Rating from their 2024-25 season,
              averaged across your selected roster. It assumes everyone maintains their current production and doesn't account for lineup synergy.
            </p>
          </ExplainBox>

          {/* Real projected stats grid */}
          <SectionCard
            title="Projected Team Statistics"
            subtitle="Based on each player's real 2024-25 BartTorvik data, averaged across your selected roster"
          >
            <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
              <StatCard
                label="Points Per Game"
                value={ra.projected_ppg?.toFixed(1)}
                context={`${ppgVsIllinois > 0 ? "+" : ""}${ppgVsIllinois.toFixed(1)} vs last Illinois team (${ILLINOIS_CONTEXT.ppg})`}
                positive={ppgVsIllinois > 0}
              />
              <StatCard
                label="Rebounds Per Game"
                value={ra.projected_rpg?.toFixed(1)}
                context={`Offensive: ${ra.projected_orpg?.toFixed(1)} · Defensive: ${ra.projected_drpg?.toFixed(1)}`}
                positive={rpgVsIllinois > 0}
              />
              <StatCard
                label="Assists Per Game"
                value={ra.projected_apg?.toFixed(1)}
                context="Based on each player's assist rate from their last season"
              />
              <StatCard
                label="Steals Per Game"
                value={ra.projected_spg?.toFixed(1)}
                context="Higher steals = more transition buckets and disruption"
                positive={ra.projected_spg > 6}
              />
              <StatCard
                label="Blocks Per Game"
                value={ra.projected_bpg?.toFixed(1)}
                context="Rim protection and deterrence for opponents driving the lane"
                positive={ra.projected_bpg > 4}
              />
              <StatCard
                label="Turnovers Per Game"
                value={ra.projected_topg?.toFixed(1)}
                context="Lower is better — each turnover is a free possession for the opponent"
                positive={ra.projected_topg < 12}
              />
              <StatCard
                label="3-Point Shooting"
                value={formatPct(ra.team_3pt_pct)}
                context={`Illinois system threshold: 36.5%. ${ra.team_3pt_pct >= 0.365 ? "✓ Above threshold" : "Below threshold"}`}
                positive={ra.team_3pt_pct >= 0.365}
              />
              <StatCard
                label="Shooting Efficiency (TS%)"
                value={formatPct(ra.team_ts_pct)}
                context="True Shooting % accounts for 2PT, 3PT, and free throws. 55%+ is efficient, 60%+ is elite."
                positive={ra.team_ts_pct >= 0.55}
              />
            </div>
          </SectionCard>

          {/* Offensive vs Defensive efficiency */}
          <div className="grid gap-4 md:grid-cols-2">
            <SectionCard
              title={`Offensive Efficiency: ${ra.team_ortg?.toFixed(1)}`}
              subtitle="Points scored per 100 possessions"
            >
              <p className="text-sm text-slate-600">
                <strong>{ra.team_ortg?.toFixed(1)} ORtg</strong> means this lineup would score{" "}
                <strong>{ra.team_ortg?.toFixed(1)} points for every 100 possessions</strong> — roughly 67 possessions per game in college basketball.
              </p>
              <div className="mt-3 space-y-1">
                <p className="text-xs text-slate-500">Context:</p>
                <p className="text-xs text-slate-500">· 115+ = elite offense (top-25 nationally)</p>
                <p className="text-xs text-slate-500">· 110–115 = very good</p>
                <p className="text-xs text-slate-500">· 105–110 = above average</p>
                <p className="text-xs text-slate-500">· Below 105 = below average</p>
                <p className={`text-xs font-semibold mt-2 ${ortgVsIllinois > 0 ? "text-green-600" : "text-red-500"}`}>
                  {ortgVsIllinois > 0 ? "▲" : "▼"} {Math.abs(ortgVsIllinois).toFixed(1)} vs last Illinois team
                </p>
              </div>
            </SectionCard>

            <SectionCard
              title={`Defensive Efficiency: ${ra.team_drtg?.toFixed(1)}`}
              subtitle="Points allowed per 100 possessions — LOWER IS BETTER"
            >
              <p className="text-sm text-slate-600">
                <strong>{ra.team_drtg?.toFixed(1)} DRtg</strong> means this lineup would allow{" "}
                <strong>{ra.team_drtg?.toFixed(1)} points for every 100 opponent possessions</strong>.
                Lower is better — great defenses give up under 96.
              </p>
              <div className="mt-3 space-y-1">
                <p className="text-xs text-slate-500">Context (lower = better defense):</p>
                <p className="text-xs text-slate-500">· Under 97 = elite defense</p>
                <p className="text-xs text-slate-500">· 97–103 = good to above average</p>
                <p className="text-xs text-slate-500">· 103–108 = average</p>
                <p className="text-xs text-slate-500">· Above 108 = poor defense</p>
                <p className={`text-xs font-semibold mt-2 ${drtgVsIllinois < 0 ? "text-green-600" : "text-red-500"}`}>
                  {drtgVsIllinois < 0 ? "▲ Better" : "▼ Worse"} by {Math.abs(drtgVsIllinois).toFixed(1)} vs last Illinois team
                </p>
              </div>
            </SectionCard>
          </div>

          {/* Strengths and weaknesses */}
          <SectionCard title="Roster Analysis" subtitle="Strengths, concerns, and Illinois system fit">
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <p className="mb-2 text-sm font-bold text-green-700">What this roster does well</p>
                <ul className="space-y-1.5">
                  {/* Generate human-language strengths from data */}
                  {ra.team_3pt_pct >= 0.365 && (
                    <li className="flex gap-2 text-sm text-slate-700">
                      <span className="mt-0.5 text-green-500">+</span>
                      <span>Strong 3-point shooting ({formatPct(ra.team_3pt_pct)}) — above Illinois's 36.5% system target. Creates spacing that opens driving lanes.</span>
                    </li>
                  )}
                  {ra.team_ortg >= 110 && (
                    <li className="flex gap-2 text-sm text-slate-700">
                      <span className="mt-0.5 text-green-500">+</span>
                      <span>Strong offensive efficiency ({ra.team_ortg?.toFixed(1)} ORtg) — scores efficiently relative to possessions used.</span>
                    </li>
                  )}
                  {ra.team_drtg <= 100 && (
                    <li className="flex gap-2 text-sm text-slate-700">
                      <span className="mt-0.5 text-green-500">+</span>
                      <span>Excellent defense ({ra.team_drtg?.toFixed(1)} DRtg) — holds opponents to under a point per possession.</span>
                    </li>
                  )}
                  {ra.projected_rpg >= 38 && (
                    <li className="flex gap-2 text-sm text-slate-700">
                      <span className="mt-0.5 text-green-500">+</span>
                      <span>Strong rebounding ({ra.projected_rpg?.toFixed(1)} RPG) — controls the glass and limits opponent second chances.</span>
                    </li>
                  )}
                  {ra.net_rating > 5 && (
                    <li className="flex gap-2 text-sm text-slate-700">
                      <span className="mt-0.5 text-green-500">+</span>
                      <span>Positive net rating ({ra.net_rating > 0 ? "+" : ""}{ra.net_rating?.toFixed(1)}) — scores more than it gives up, which drives wins.</span>
                    </li>
                  )}
                  {result.strengths.slice(0, 2).map(s => (
                    <li key={s} className="flex gap-2 text-sm text-slate-700">
                      <span className="mt-0.5 text-green-500">+</span>
                      <span>{s}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="mb-2 text-sm font-bold text-red-600">Concerns to address</p>
                <ul className="space-y-1.5">
                  {ra.team_3pt_pct < 0.33 && (
                    <li className="flex gap-2 text-sm text-slate-700">
                      <span className="mt-0.5 text-red-400">−</span>
                      <span>Below-threshold 3-point shooting ({formatPct(ra.team_3pt_pct)}) — Illinois needs 36.5%+ for spacing to work in Underwood's offense.</span>
                    </li>
                  )}
                  {ra.team_drtg > 105 && (
                    <li className="flex gap-2 text-sm text-slate-700">
                      <span className="mt-0.5 text-red-400">−</span>
                      <span>Defensive rating of {ra.team_drtg?.toFixed(1)} is average or below — this lineup could struggle in Big Ten defensive slugfests.</span>
                    </li>
                  )}
                  {ra.projected_topg > 14 && (
                    <li className="flex gap-2 text-sm text-slate-700">
                      <span className="mt-0.5 text-red-400">−</span>
                      <span>High turnover rate ({ra.projected_topg?.toFixed(1)} per game) — turns possessions into free transition buckets for opponents.</span>
                    </li>
                  )}
                  {result.weaknesses.slice(0, 2).map(s => (
                    <li key={s} className="flex gap-2 text-sm text-slate-700">
                      <span className="mt-0.5 text-red-400">−</span>
                      <span>{s}</span>
                    </li>
                  ))}
                  {ra.team_3pt_pct >= 0.33 && ra.team_drtg <= 105 && ra.projected_topg <= 14 && (
                    <li className="flex gap-2 text-sm text-slate-700">
                      <span className="mt-0.5 text-yellow-500">!</span>
                      <span>This lineup profiles well statistically. Verify role acceptance and scheme fit through recruiting conversations before committing scholarships.</span>
                    </li>
                  )}
                </ul>
              </div>
            </div>
          </SectionCard>

          {/* How every stat was calculated */}
          <SectionCard title="How Every Number Was Calculated" subtitle="Full methodology — no black box">
            <div className="space-y-2">
              <ExplainBox title="Points Per Game — how we get this number">
                <p>
                  Each player&apos;s individual PPG (from their 2024-25 season) is weighted by their usage rate
                  (how often they used a possession while on the floor). Players who control more possessions get weighted more heavily.
                  The result is scaled to a 5-player starting unit. <strong>This is not a prediction — it&apos;s a projection
                  based on their existing production if they all played together.</strong>
                </p>
              </ExplainBox>
              <ExplainBox title="Rebounds Per Game — how we get this number">
                <p>
                  Each player&apos;s offensive and defensive rebound rates (% of available rebounds they grabbed while on the floor)
                  are averaged across the roster and then scaled to a typical college game with ~67 possessions.
                  Offensive rebounds = second-chance points; defensive rebounds = preventing them.
                </p>
              </ExplainBox>
              <ExplainBox title="Offensive and Defensive Efficiency Ratings — what they mean">
                <p>
                  <strong>Offensive Rating (ORtg)</strong>: points scored per 100 possessions.
                  Averages each player&apos;s individual ORtg from their last season.
                  This controls for pace — a fast-paced team might score more points per game but be less efficient per possession.
                  <br /><br />
                  <strong>Defensive Rating (DRtg)</strong>: points allowed per 100 possessions while that player is on the floor.
                  Lower is better. Averages each player&apos;s individual DRtg. Reflects on-ball defense, help defense, and team defensive scheme fit.
                </p>
              </ExplainBox>
              <ExplainBox title="Win projection — how 'projected wins' is calculated">
                <p>
                  Net Rating = Offensive Rating − Defensive Rating. This is the most predictive team stat in basketball.
                  Win projection formula: <strong>20 + (Net Rating × 0.65)</strong>.
                  Starting point is 20 wins (average Big Ten team). Every +1.5 net rating points adds roughly 1 win.
                  Capped between 10 and 35 wins to prevent impossible values.
                  <br /><br />
                  <strong>Important caveat</strong>: this assumes all players maintain their current production in a new team context.
                  In reality, role changes, chemistry, and coaching impact can shift projections ±4–6 wins.
                </p>
              </ExplainBox>
              <ExplainBox title="3-Point Shooting — why 36.5% is the threshold">
                <p>
                  Illinois&apos;s offense under Brad Underwood is built around 3-point volume and spacing.
                  The 36.5% threshold is based on the minimum efficiency needed for defenders to respect the shot
                  and stay attached — below that, opponents can cheat off shooters and take away driving lanes.
                  <strong>Team 3PT% below 33% is a serious concern for Underwood&apos;s system.</strong>
                </p>
              </ExplainBox>
              <ExplainBox title="Data source — are these real numbers?">
                <p>
                  All player statistics are <strong>real 2024-25 BartTorvik advanced stats</strong> scraped from barttorvik.com.
                  PPG, rebounds, assists, ORtg, DRtg, TS%, 3PT%, and other metrics are the actual values from this past season.
                  The <em>projections</em> (what a new combined team would do) are calculated estimates — not guaranteed outcomes.
                  Think of them as a well-informed starting point for roster construction conversations, not a certified prediction.
                </p>
              </ExplainBox>
            </div>
          </SectionCard>
        </>
      )}

      {selected.length === 0 && (
        <div className="flex h-48 flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-200 bg-slate-50">
          <p className="text-lg font-bold text-slate-400">No players selected yet</p>
          <p className="mt-1 text-sm text-slate-400">Search above and click any player to build your hypothetical roster</p>
          <p className="mt-2 text-xs text-slate-300">Try: Cooper Flagg, Johni Broome, or search a school like "Duke"</p>
        </div>
      )}
    </div>
  );
}
