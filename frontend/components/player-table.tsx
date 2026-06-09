import { Player, formatPct } from "@/lib/api";

function ActionTag({ risk, fit, success }: { risk: number; fit: number; success: number }) {
  let label = "Film Review";
  let cls = "bg-yellow-50 text-yellow-700 border-yellow-200";

  if (risk < 35 && fit >= 60 && success >= 70) {
    label = "Prioritize";
    cls = "bg-green-50 text-green-700 border-green-200";
  } else if (risk >= 60) {
    label = "High Risk";
    cls = "bg-red-50 text-red-600 border-red-200";
  } else if (risk < 50 && fit >= 50 && success >= 55) {
    label = "Watchlist";
    cls = "bg-blue-50 text-blue-700 border-blue-200";
  }

  return (
    <span className={`inline-block rounded-full border px-2 py-0.5 text-[10px] font-semibold ${cls}`}>
      {label}
    </span>
  );
}

function RiskBadge({ value }: { value: number }) {
  const cls =
    value < 35 ? "text-green-700 bg-green-50" :
    value < 55 ? "text-yellow-700 bg-yellow-50" :
    "text-red-600 bg-red-50";
  const label = value < 35 ? "Low" : value < 55 ? "Mod" : "High";
  return (
    <span className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-bold ${cls}`}>
      {label} {value.toFixed(0)}
    </span>
  );
}

export function PlayerTable({ players }: { players: Player[] }): JSX.Element {
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-50 text-[11px] text-slate-500">
          <tr>
            <th className="px-3 py-2 text-left font-semibold">Player</th>
            <th className="px-2 py-2 text-center font-semibold">Pos</th>
            <th className="px-3 py-2 text-left font-semibold">School</th>
            <th className="px-2 py-2 text-center font-semibold" title="3-point shooting percentage — Illinois system threshold: 36.5%">3PT%</th>
            <th className="px-2 py-2 text-center font-semibold" title="Illinois Fit Score (0-100): how well the player's profile matches Underwood's system. 65+ = strong fit.">IL Fit</th>
            <th className="px-2 py-2 text-center font-semibold" title="Transfer Translation Score (0-100): how likely current production carries to Big Ten rotation. 70+ = strong.">Translation</th>
            <th className="px-2 py-2 text-center font-semibold" title="Risk Score (0-100, LOWER IS SAFER): penalizes small sample, turnovers, poor efficiency, role mismatch.">Risk ▲</th>
            <th className="px-2 py-2 text-center font-semibold" title="Hidden Gem Score (0-100): production relative to dataset rank. Higher = undervalued vs. attention level.">Gem</th>
            <th className="px-2 py-2 text-center font-semibold">Action</th>
          </tr>
        </thead>
        <tbody>
          {players.map((player) => (
            <tr key={player.player_name} className="border-t border-slate-100 hover:bg-slate-50">
              <td className="px-3 py-2 font-semibold text-navy">{player.player_name}</td>
              <td className="px-2 py-2 text-center text-slate-500">{player.position}</td>
              <td className="px-3 py-2 text-slate-600">{player.school}</td>
              <td className="px-2 py-2 text-center">
                <span className={player.three_pt_pct >= 0.365 ? "font-bold text-green-700" : player.three_pt_pct < 0.32 ? "text-red-500" : "text-slate-700"}>
                  {formatPct(player.three_pt_pct)}
                </span>
              </td>
              <td className="px-2 py-2 text-center">
                <span className={player.illinois_fit_score >= 65 ? "font-bold text-green-700" : player.illinois_fit_score >= 50 ? "text-slate-700" : "text-red-500"}>
                  {player.illinois_fit_score.toFixed(0)}
                </span>
              </td>
              <td className="px-2 py-2 text-center">
                <span className={player.transfer_success_score >= 70 ? "font-bold text-green-700" : player.transfer_success_score >= 50 ? "text-slate-700" : "text-red-500"}>
                  {player.transfer_success_score.toFixed(0)}
                </span>
              </td>
              <td className="px-2 py-2 text-center">
                <RiskBadge value={player.risk_score} />
              </td>
              <td className="px-2 py-2 text-center text-slate-600">{player.hidden_gem_score.toFixed(0)}</td>
              <td className="px-2 py-2 text-center">
                <ActionTag risk={player.risk_score} fit={player.illinois_fit_score} success={player.transfer_success_score} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="border-t border-slate-100 px-3 py-1.5 text-[10px] text-slate-400">
        IL Fit = Illinois Fit Score | Translation = Transfer Translation Score | Risk: lower is safer | Gem = Hidden Gem Score (0-100)
      </div>
    </div>
  );
}
