"use client";

import { useEffect, useMemo, useState } from "react";

import Plot from "@/components/plot";
import { PlayerTable } from "@/components/player-table";
import { SectionCard } from "@/components/section-card";
import { Player, apiGet } from "@/lib/api";

type GemResponse = {
  top_hidden_gems: Player[];
  top_underrated_players: Player[];
  top_overrated_players: Player[];
  rank_vs_impact: Array<{
    player_name: string;
    public_transfer_rank: number;
    projected_impact_score: number;
    market_inefficiency_score: number;
  }>;
};

export default function HiddenGemLabPage(): JSX.Element {
  const [data, setData] = useState<GemResponse | null>(null);

  useEffect(() => {
    apiGet<GemResponse>("/hidden-gem-lab").then(setData);
  }, []);

  const hiddenQuadrant = useMemo(
    () =>
      (data?.rank_vs_impact ?? []).filter(
        (item) => item.projected_impact_score >= 70 && item.public_transfer_rank >= 45,
      ),
    [data],
  );

  return (
    <div className="space-y-6">
      <SectionCard title="Hidden Gem Lab" subtitle="Players our scoring model values higher than their dataset rank — potential value targets before market catches up.">
        <div className="grid gap-3 md:grid-cols-3 text-sm">
          <div className="rounded border border-slate-200 bg-slate-50 p-3">
            <p className="font-semibold text-navy">Hidden Gem Score (0-100)</p>
            <p className="mt-1 text-slate-600">Production relative to dataset rank. High score = strong metrics relative to market attention. Does NOT mean the player is secretly elite — verify with film.</p>
          </div>
          <div className="rounded border border-slate-200 bg-slate-50 p-3">
            <p className="font-semibold text-navy">Value Gap Score (0-100)</p>
            <p className="mt-1 text-slate-600">The gap between where our model ranks a player vs. where their dataset rank places them. High gap = model sees more value than market does. Act quickly — these windows close.</p>
          </div>
          <div className="rounded border border-slate-200 bg-slate-50 p-3">
            <p className="font-semibold text-orange">Dataset Rank Note</p>
            <p className="mt-1 text-slate-600">The &quot;public rank&quot; field is a prototype dataset rank (1-150), NOT from ESPN, Rivals, or On3. It models market attention for demonstration purposes only.</p>
          </div>
        </div>
      </SectionCard>

      <div className="grid gap-4 xl:grid-cols-2">
        <SectionCard title="Hidden Gems" subtitle="Players our model likes more than the market does — move on these before competitors catch up">
          <PlayerTable players={data?.top_hidden_gems ?? []} />
        </SectionCard>
        <SectionCard title="Undervalued Targets" subtitle="Strong production, lower reputation — potential value adds for Illinois">
          <PlayerTable players={data?.top_underrated_players ?? []} />
        </SectionCard>
      </div>

      <SectionCard title="Potentially Overvalued" subtitle="Market attention ahead of what the stats support — proceed carefully">
        <PlayerTable players={data?.top_overrated_players ?? []} />
      </SectionCard>

      <SectionCard
        title="Dataset Rank vs Projected Impact"
        subtitle="Orange = players where our model sees more value than their dataset rank suggests. These are your targeting opportunities."
      >
        <p className="mb-3 text-xs text-slate-500">
          X-axis: dataset rank (lower number = higher-profile player). Y-axis: projected rotation impact.
          Orange dots in the upper-right = players ranked low who project well — the hidden gem zone.
        </p>
        <Plot
          data={[
            {
              x: (data?.rank_vs_impact ?? []).map((p) => p.public_transfer_rank),
              y: (data?.rank_vs_impact ?? []).map((p) => p.projected_impact_score),
              text: (data?.rank_vs_impact ?? []).map((p) => p.player_name),
              mode: "markers",
              type: "scatter",
              marker: { size: 9, color: "#13294B", opacity: 0.6 },
              name: "Full Portal Board",
            },
            {
              x: hiddenQuadrant.map((p) => p.public_transfer_rank),
              y: hiddenQuadrant.map((p) => p.projected_impact_score),
              text: hiddenQuadrant.map((p) => p.player_name),
              mode: "markers",
              type: "scatter",
              marker: { size: 11, color: "#FF5F05" },
              name: "Hidden Gem Zone",
            },
          ]}
          layout={{
            autosize: true,
            paper_bgcolor: "rgba(0,0,0,0)",
            plot_bgcolor: "rgba(0,0,0,0)",
            xaxis: { title: "Dataset Rank (right = lower-profile players)", autorange: "reversed" },
            yaxis: { title: "Projected Rotation Impact Score" },
            margin: { t: 20, l: 40, r: 20, b: 45 },
          }}
          style={{ width: "100%", height: 430 }}
          config={{ displayModeBar: false }}
        />
      </SectionCard>
    </div>
  );
}
