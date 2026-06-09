"use client";

import { useEffect, useState } from "react";

import Plot from "@/components/plot";
import { SectionCard } from "@/components/section-card";
import { Player, apiGet, apiPost, formatPct } from "@/lib/api";

type PlayersResponse = { items: Player[] };

type CompareResponse = {
  player_a: Player;
  player_b: Player;
  recommendation: string;
  advantages: {
    player_a: string[];
    player_b: string[];
  };
};

export default function ComparePlayersPage(): JSX.Element {
  const [players, setPlayers] = useState<Player[]>([]);
  const [playerA, setPlayerA] = useState("");
  const [playerB, setPlayerB] = useState("");
  const [result, setResult] = useState<CompareResponse | null>(null);

  useEffect(() => {
    apiGet<PlayersResponse>("/players?limit=200").then((res) => {
      const sorted = [...res.items].sort((a, b) =>
        a.player_name.localeCompare(b.player_name)
      );
      setPlayers(sorted);
      if (sorted.length > 1) {
        setPlayerA(sorted[0].player_name);
        setPlayerB(sorted[1].player_name);
      }
    });
  }, []);

  async function runCompare(): Promise<void> {
    if (!playerA || !playerB) return;
    const data = await apiPost<CompareResponse>("/compare", { player_a: playerA, player_b: playerB });
    setResult(data);
  }

  useEffect(() => {
    runCompare();
  }, [playerA, playerB]);

  return (
    <div className="space-y-6">
      <SectionCard
        title="Compare Players"
        subtitle="Side-by-side comparison of any two portal players — stats, fit, risk, and a staff recommendation."
      >
        <p className="mb-3 text-xs text-slate-500">
          Search and select any two players from the 197-player portal board. The comparison uses real 2024-25 BartTorvik stats.
        </p>
        <div className="grid gap-3 md:grid-cols-2">
          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-500">Player 1</label>
            <select
              className="h-11 w-full rounded-lg border border-slate-300 px-3 text-sm"
              value={playerA}
              onChange={(e) => setPlayerA(e.target.value)}
            >
              {players.map((p) => (
                <option key={p.player_name} value={p.player_name}>
                  {p.player_name} — {p.position} · {p.school}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-semibold text-slate-500">Player 2</label>
            <select
              className="h-11 w-full rounded-lg border border-slate-300 px-3 text-sm"
              value={playerB}
              onChange={(e) => setPlayerB(e.target.value)}
            >
              {players.map((p) => (
                <option key={p.player_name} value={p.player_name}>
                  {p.player_name} — {p.position} · {p.school}
                </option>
              ))}
            </select>
          </div>
        </div>
      </SectionCard>

      {result && (
        <div className="rounded-xl border border-navy/20 bg-navy/5 p-4">
          <p className="text-[10px] font-bold uppercase tracking-wider text-navy/60">Staff Recommendation</p>
          <p className="mt-1 text-sm font-semibold text-navy">{result.recommendation}</p>
        </div>
      )}

      {result && (
        <div className="grid gap-4 md:grid-cols-2">
          {([
            { player: result.player_a, advantages: result.advantages.player_a, color: "navy" },
            { player: result.player_b, advantages: result.advantages.player_b, color: "orange" },
          ] as const).map(({ player, advantages, color }) => (
            <div key={player.player_name} className={`rounded-xl border p-4 ${color === "navy" ? "border-navy/20 bg-navy/5" : "border-orange/20 bg-orange/5"}`}>
              <p className={`font-bold text-lg ${color === "navy" ? "text-navy" : "text-orange"}`}>{player.player_name}</p>
              <p className="text-xs text-slate-500 mb-2">{player.position} · {player.school} · {player.conference}</p>
              <div className="grid grid-cols-3 gap-2 mb-3 text-center">
                <div className="rounded bg-white/70 p-2">
                  <p className="text-[10px] text-slate-400">IL Fit</p>
                  <p className="font-bold text-navy">{player.illinois_fit_score?.toFixed(0)}</p>
                </div>
                <div className="rounded bg-white/70 p-2">
                  <p className="text-[10px] text-slate-400">Success %</p>
                  <p className="font-bold text-navy">{player.transfer_success_score?.toFixed(0)}</p>
                </div>
                <div className="rounded bg-white/70 p-2">
                  <p className="text-[10px] text-slate-400">3PT%</p>
                  <p className="font-bold text-navy">{formatPct(player.three_pt_pct)}</p>
                </div>
              </div>
              <p className="text-xs font-semibold text-slate-600 mb-1">Advantages:</p>
              <ul className="space-y-1">
                {advantages.map(a => (
                  <li key={a} className="flex gap-1.5 text-xs text-slate-700">
                    <span className="text-green-500 mt-0.5">+</span> {a}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}

      <SectionCard title="Head-to-Head Profile" subtitle="Illinois Fit · Likelihood to Succeed · Safety (higher = safer) · 3PT Shooting · Defensive Efficiency">
        <p className="mb-3 text-xs text-slate-500">
          All axes: higher = better. Safety = 100 minus Risk Score, so a safe player (low risk) scores high here.
          Shooting = 3PT% scaled to 0-65. Defense = how much better than average the player&apos;s defensive rating is.
        </p>
        <Plot
          data={[
            {
              type: "scatterpolar",
              theta: ["Illinois Fit", "Likely to Succeed", "Safety", "3PT Shooting", "Defense", "Illinois Fit"],
              r: result
                ? [
                    result.player_a.illinois_fit_score,
                    result.player_a.transfer_success_score,
                    100 - result.player_a.risk_score,
                    result.player_a.three_pt_pct * 100,
                    Math.max(0, 120 - result.player_a.defensive_rating),
                    result.player_a.illinois_fit_score,
                  ]
                : [],
              fill: "toself",
              name: result?.player_a.player_name ?? "Player A",
              line: { color: "#13294B" },
              fillcolor: "rgba(19,41,75,0.2)",
            },
            {
              type: "scatterpolar",
              theta: ["Illinois Fit", "Likely to Succeed", "Safety", "3PT Shooting", "Defense", "Illinois Fit"],
              r: result
                ? [
                    result.player_b.illinois_fit_score,
                    result.player_b.transfer_success_score,
                    100 - result.player_b.risk_score,
                    result.player_b.three_pt_pct * 100,
                    Math.max(0, 120 - result.player_b.defensive_rating),
                    result.player_b.illinois_fit_score,
                  ]
                : [],
              fill: "toself",
              name: result?.player_b.player_name ?? "Player B",
              line: { color: "#FF5F05" },
              fillcolor: "rgba(255,95,5,0.2)",
            },
          ]}
          layout={{
            paper_bgcolor: "rgba(0,0,0,0)",
            polar: { radialaxis: { visible: true, range: [0, 100] } },
            margin: { t: 20, l: 20, r: 20, b: 20 },
            legend: { orientation: "h", y: -0.1 },
          }}
          style={{ width: "100%", height: 430 }}
          config={{ displayModeBar: false }}
        />
      </SectionCard>
    </div>
  );
}
