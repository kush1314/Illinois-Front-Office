"use client";

import Link from "next/link";
import { ScoreBadge } from "@/components/score-badge";
import { ExternalLink } from "lucide-react";

export type PlayerCardData = {
  player_name: string;
  school: string;
  conference?: string;
  position: string;
  class?: string;
  three_pt_pct?: number;
  illinois_fit_score?: number;
  transfer_success_score?: number;
  risk_score?: number;
  hidden_gem_score?: number;
  market_inefficiency_score?: number;
  archetype?: string;
};

type Props = {
  player: PlayerCardData;
  showScores?: boolean;
  compact?: boolean;
  actions?: React.ReactNode;
};

export function PlayerCard({ player, showScores = true, compact = false, actions }: Props): JSX.Element {
  const initials = player.player_name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <div className="group rounded-xl border border-gray-100 bg-white p-4 shadow-sm transition hover:shadow-md">
      <div className="flex items-start gap-3">
        {/* Avatar */}
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-navy text-sm font-bold text-white">
          {initials}
        </div>

        {/* Name + school */}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className={`font-bold text-gray-900 ${compact ? "text-sm" : "text-base"} truncate`}>
              {player.player_name}
            </h3>
            {player.archetype && (
              <span className="shrink-0 rounded-full bg-navy/10 px-2 py-0.5 text-[10px] font-semibold text-navy">
                {player.archetype}
              </span>
            )}
          </div>
          <p className="mt-0.5 text-xs text-gray-500">
            {player.position} · {player.school}
            {player.conference ? ` (${player.conference})` : ""}
            {player.class ? ` · ${player.class}` : ""}
          </p>
          {player.three_pt_pct != null && (
            <p className="mt-0.5 text-xs text-gray-400">3PT: {(player.three_pt_pct * 100).toFixed(1)}%</p>
          )}
        </div>

        {/* Link to intelligence page */}
        <Link
          href={`/player-intelligence?name=${encodeURIComponent(player.player_name)}`}
          className="shrink-0 text-gray-300 transition hover:text-orange"
          title="View player"
        >
          <ExternalLink className="h-4 w-4" />
        </Link>
      </div>

      {/* Scores grid */}
      {showScores && !compact && (
        <>
          <div className="mt-3 grid grid-cols-2 gap-1.5">
            {player.illinois_fit_score != null && (
              <ScoreBadge label="IL Fit Score" value={player.illinois_fit_score} size="sm" showBar />
            )}
            {player.transfer_success_score != null && (
              <ScoreBadge label="Translation Score" value={player.transfer_success_score} size="sm" showBar />
            )}
            {player.risk_score != null && (
              <ScoreBadge label="Risk (lower=safer)" value={player.risk_score} variant={player.risk_score > 60 ? "danger" : player.risk_score > 40 ? "warning" : "success"} size="sm" showBar />
            )}
            {player.hidden_gem_score != null && (
              <ScoreBadge label="Hidden Gem" value={player.hidden_gem_score} size="sm" showBar />
            )}
          </div>
          {/* Action tag */}
          {player.risk_score != null && player.illinois_fit_score != null && player.transfer_success_score != null && (
            <div className="mt-2">
              {player.risk_score < 35 && player.illinois_fit_score >= 60 && player.transfer_success_score >= 70 ? (
                <span className="inline-block rounded-full bg-green-50 border border-green-200 px-2 py-0.5 text-[10px] font-semibold text-green-700">
                  PRIORITIZE — contact immediately
                </span>
              ) : player.risk_score >= 60 ? (
                <span className="inline-block rounded-full bg-red-50 border border-red-200 px-2 py-0.5 text-[10px] font-semibold text-red-600">
                  HIGH RISK — proceed with diligence
                </span>
              ) : player.risk_score < 50 && player.illinois_fit_score >= 50 ? (
                <span className="inline-block rounded-full bg-blue-50 border border-blue-200 px-2 py-0.5 text-[10px] font-semibold text-blue-700">
                  WATCHLIST — schedule film review
                </span>
              ) : (
                <span className="inline-block rounded-full bg-yellow-50 border border-yellow-200 px-2 py-0.5 text-[10px] font-semibold text-yellow-700">
                  FILM REVIEW — verify role fit
                </span>
              )}
            </div>
          )}
        </>
      )}

      {actions && <div className="mt-3 flex gap-2">{actions}</div>}
    </div>
  );
}
