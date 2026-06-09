"use client";

import { useEffect, useState } from "react";

import Plot from "@/components/plot";
import { PlayerTable } from "@/components/player-table";
import { SectionCard } from "@/components/section-card";
import { Player, apiPost, formatPct } from "@/lib/api";

type RecruitingResponse = {
  top_targets: Player[];
  top_hidden_gems: Player[];
  top_value_players: Player[];
  top_high_upside_players: Player[];
  gm_priority_board: Player[];
  organization_fit_board: Player[];
  safe_floor_board: Player[];
  swing_bets_board: Player[];
  role_boards: {
    wing_defenders: Player[];
    lead_guards: Player[];
    stretch_bigs: Player[];
    rim_protectors: Player[];
  };
  overvalued_risk_board: Player[];
  illinois_roster_needs: string[];
  summary_metrics: {
    avg_fit_top_targets: number;
    avg_risk_top_targets: number;
    avg_hidden_gem_top_targets: number;
    avg_projected_impact_top_targets: number;
  };
};

function RoleBoard({ title, players }: { title: string; players: Player[] }): JSX.Element {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3">
      <p className="mb-2 text-sm font-semibold text-navy">{title}</p>
      <div className="space-y-2">
        {players.slice(0, 5).map((p) => (
          <div key={p.player_name} className="rounded-md bg-slate-50 p-2 text-xs">
            <p className="font-semibold text-slate-800">{p.player_name}</p>
            <p className="text-slate-600">
              {p.position} | Fit {p.illinois_fit_score.toFixed(1)} | Risk {p.risk_score.toFixed(1)} | 3PT {formatPct(p.three_pt_pct)}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function RecruitingCenterPage(): JSX.Element {
  const [data, setData] = useState<RecruitingResponse | null>(null);

  useEffect(() => {
    apiPost<RecruitingResponse>("/recruiting/targets", {
      position: "Any",
      max_risk: 70,
      min_shooting: 0.31,
      min_defense: 55,
      min_rebounding: 35,
      min_playmaking: 35,
    }).then(setData);
  }, []);

  return (
    <div className="space-y-6">
      <SectionCard title="Recruiting Center" subtitle="Transfer portal targets ranked and filtered for Illinois's system — real 2024-25 stats from BartTorvik.">
        <p className="text-sm text-slate-600">
          Overview of the best available portal additions for Illinois. Each board is calculated from actual player statistics —
          not guesswork. Scroll down to see the GM Priority Board (best overall mix), role-specific shortlists, hidden value targets, and safe-floor additions.
        </p>
        <div className="mt-3 rounded-lg bg-navy/5 border border-navy/15 p-3 text-xs text-navy">
          <strong>How to read the table columns:</strong>{" "}
          <span className="text-slate-600">
            <strong>3PT%</strong> = 3-point shooting (Illinois threshold: 36.5% — below this, defenders can ignore you) ·
            <strong> IL Fit</strong> = Illinois system match score out of 100 (65+ = strong fit for Underwood&apos;s scheme) ·
            <strong> Translation</strong> = likelihood their production carries to Illinois out of 100 (70+ = high confidence) ·
            <strong> Risk</strong> = lower is safer; penalizes small samples, high turnovers, poor efficiency ·
            <strong> Gem</strong> = how undervalued they are vs their dataset rank (100 = maximum hidden value) ·
            <strong> Action</strong> = recommended next step for Illinois staff
          </span>
        </div>
      </SectionCard>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">System Fit (top 10)</p>
          <p className="text-3xl font-extrabold text-navy">{data?.summary_metrics.avg_fit_top_targets.toFixed(1) ?? "-"}<span className="text-lg">/100</span></p>
          <p className="mt-1 text-xs text-slate-500">65+ = strong Underwood system match</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Safety Level (top 10)</p>
          <p className={`text-3xl font-extrabold ${(data?.summary_metrics.avg_risk_top_targets ?? 100) < 40 ? "text-green-600" : "text-yellow-600"}`}>
            {data?.summary_metrics.avg_risk_top_targets.toFixed(1) ?? "-"}<span className="text-lg">/100</span>
          </p>
          <p className="mt-1 text-xs text-slate-500">Lower is safer — under 40 is low risk</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Hidden Value Score (top 10)</p>
          <p className="text-3xl font-extrabold text-navy">{data?.summary_metrics.avg_hidden_gem_top_targets.toFixed(1) ?? "-"}<span className="text-lg">/100</span></p>
          <p className="mt-1 text-xs text-slate-500">Higher = more undervalued vs. dataset rank</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Rotation Impact (top 10)</p>
          <p className="text-3xl font-extrabold text-navy">{data?.summary_metrics.avg_projected_impact_top_targets.toFixed(1) ?? "-"}<span className="text-lg">/100</span></p>
          <p className="mt-1 text-xs text-slate-500">Projected contribution in a Big Ten rotation</p>
        </div>
      </div>

      <SectionCard title="What Illinois Needs" subtitle="Based on real 2024-25 Illinois roster stats — here's what the numbers say about the gaps.">
        <div className="mb-3 rounded-lg bg-amber-50 border border-amber-200 p-3 text-xs text-amber-800">
          <strong>Why these gaps?</strong> Illinois&apos;s current roster averages 32.3% from three — below Underwood&apos;s 36.5% minimum for spacing to work.
          Jakucionis (31.8%), Boswell (24.5%), and White (32.9%) are all below threshold. Without reliable shooters, defenses pack the paint and shut down the drive-and-kick system.
        </div>
        <ul className="space-y-3">
          {(data?.illinois_roster_needs ?? []).map((need) => (
            <li key={need} className="flex items-start gap-2 text-sm text-slate-700">
              <span className="mt-0.5 shrink-0 text-orange font-bold text-base">→</span>
              <span>{need}</span>
            </li>
          ))}
        </ul>
        <p className="mt-3 text-xs text-slate-400">
          Data: 2024-25 Illinois roster from BartTorvik. Threshold benchmarks from Underwood&apos;s system requirements.
        </p>
      </SectionCard>

      <SectionCard
        title="GM Priority Board"
        subtitle="Best overall mix of Illinois fit, projected impact, market value, and manageable risk — your Tier 1 contact list."
      >
        <PlayerTable players={data?.gm_priority_board ?? []} />
      </SectionCard>

      <div className="grid gap-4 xl:grid-cols-2">
        <SectionCard
          title="Best System Fits"
          subtitle="Players whose statistical profiles best match Underwood's 3PT-heavy, switching defense requirements."
        >
          <PlayerTable players={data?.organization_fit_board ?? []} />
        </SectionCard>
        <SectionCard
          title="Hidden Gems"
          subtitle="Players our model values higher than their dataset rank — move before competing programs catch up."
        >
          <PlayerTable players={data?.top_hidden_gems ?? []} />
        </SectionCard>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <SectionCard
          title="Safe Floor Targets"
          subtitle="Low-risk additions — proven production, manageable role jump, high floor. Good for scholarship certainty."
        >
          <PlayerTable players={data?.safe_floor_board ?? []} />
        </SectionCard>

        <SectionCard
          title="High-Upside Bets"
          subtitle="Higher ceiling but more volatility — worth one scholarship if you can absorb the risk."
        >
          <PlayerTable players={data?.swing_bets_board ?? []} />
        </SectionCard>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <SectionCard
          title="Best Value vs Market"
          subtitle="Players producing more than their reputation suggests — value Illinois can capture before bidding wars start."
        >
          <PlayerTable players={data?.top_value_players ?? []} />
        </SectionCard>
        <SectionCard
          title="Highest Projected Impact"
          subtitle="Players whose stats and model scores project the strongest contribution in a Big Ten rotation."
        >
          <PlayerTable players={data?.top_high_upside_players ?? []} />
        </SectionCard>
      </div>

      <SectionCard
        title="Role-Specific Shortlists"
        subtitle="Filtered boards by Illinois's known positional needs — use these for your next recruiting call."
      >
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <RoleBoard title="3-and-D Wings" players={data?.role_boards.wing_defenders ?? []} />
          <RoleBoard title="Playmaking Guards" players={data?.role_boards.lead_guards ?? []} />
          <RoleBoard title="Stretch Bigs (can shoot)" players={data?.role_boards.stretch_bigs ?? []} />
          <RoleBoard title="Rim Protectors" players={data?.role_boards.rim_protectors ?? []} />
        </div>
      </SectionCard>

      <SectionCard
        title="Caution: Potentially Overvalued"
        subtitle="Players the market may be paying up for that our model doesn't support at that price — approach carefully."
      >
        <PlayerTable players={data?.overvalued_risk_board ?? []} />
      </SectionCard>

      <SectionCard
        title="Risk vs Value Chart"
        subtitle="X-axis: how risky (lower left = safer). Y-axis: how undervalued vs market (higher = better deal). Dot size = projected impact. Color = Illinois fit."
      >
        <p className="mb-2 text-xs text-slate-500">
          Best targets are in the <strong>lower-right</strong>: low risk, high value gap.
          Avoid upper-left: high risk, overvalued relative to what the stats support.
        </p>
        <Plot
          data={[
            {
              x: (data?.gm_priority_board ?? []).map((p) => p.risk_score),
              y: (data?.gm_priority_board ?? []).map((p) => p.market_inefficiency_score),
              text: (data?.gm_priority_board ?? []).map((p) => p.player_name),
              mode: "markers",
              type: "scatter",
              marker: {
                color: (data?.gm_priority_board ?? []).map((p) => p.illinois_fit_score),
                colorscale: "Blues",
                size: (data?.gm_priority_board ?? []).map((p) => Math.max(10, p.projected_impact_score / 8)),
                showscale: true,
                colorbar: { title: "IL Fit" },
              },
            },
          ]}
          layout={{
            autosize: true,
            paper_bgcolor: "rgba(0,0,0,0)",
            plot_bgcolor: "rgba(0,0,0,0)",
            xaxis: { title: "Risk Level (lower = safer)" },
            yaxis: { title: "How Undervalued vs Market (higher = better deal)" },
            margin: { t: 20, l: 50, r: 20, b: 45 },
          }}
          style={{ width: "100%", height: 380 }}
          config={{ displayModeBar: false }}
        />
      </SectionCard>

    </div>
  );
}
