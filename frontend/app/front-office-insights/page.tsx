"use client";

import { useEffect, useState } from "react";
import { SectionCard } from "@/components/section-card";
import { apiGet } from "@/lib/api";

type InsightCard = { title: string; player: string; summary: string };
type SimilarTarget = { player_name: string; school: string; position: string; illinois_fit_score?: number; transfer_success_score?: number };

type InsightsResponse = {
  insights: InsightCard[];
  special_targets: {
    most_similar_to_terrence_shannon_jr?: SimilarTarget[];
    most_similar_to_kasparas_jakucionis?: SimilarTarget[];
    most_similar_to_current_illinois_needs?: SimilarTarget[];
  };
};

const ACTION_LABELS: Record<string, string> = {
  "Most Undervalued Shooter":       "Prioritize for spacing role",
  "Most Undervalued Defender":      "Film review — confirm switching ability",
  "Highest Upside Freshman Transfer":"Monitor — ceiling dependent on role clarity",
  "Best Value Wing":                "Watchlist — fit depends on roster balance",
  "Most NBA-Like Prospect":         "Film review — confirm translation to Big Ten physicality",
};

export default function FrontOfficeInsightsPage(): JSX.Element {
  const [data, setData] = useState<InsightsResponse | null>(null);

  useEffect(() => {
    apiGet<InsightsResponse>("/insights").then(setData);
  }, []);

  return (
    <div className="space-y-6">
      <SectionCard
        title="Front Office Insights"
        subtitle="Auto-generated intelligence cards for each key roster dimension — prototype demo dataset."
      >
        <p className="text-sm text-slate-600">
          These cards identify the top candidate for each front-office priority using the Illinois scoring model.
          All players are from the prototype demo dataset (synthetic profiles, not live portal data).
        </p>
      </SectionCard>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {(data?.insights ?? []).map((card) => (
          <div key={card.title} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="mb-2 flex items-start justify-between gap-2">
              <p className="font-bold text-navy">{card.title}</p>
              {ACTION_LABELS[card.title] && (
                <span className="shrink-0 rounded-full bg-orange/10 px-2 py-0.5 text-[10px] font-semibold text-orange">
                  {ACTION_LABELS[card.title]}
                </span>
              )}
            </div>
            <p className="mb-2 text-base font-semibold text-slate-800">{card.player}</p>
            <p className="text-xs leading-relaxed text-slate-600">{card.summary}</p>
            <p className="mt-2 text-[10px] text-slate-400">
              Scores: Transfer Translation Score (0-100) · Illinois Fit (0-100) · Hidden Gem (0-100). Higher = better for each.
            </p>
          </div>
        ))}
      </div>

      <SectionCard title="Similarity Targets" subtitle="Profile comparisons to known Illinois players and roster needs">
        {data?.special_targets && (
          <div className="space-y-4">
            {Object.entries(data.special_targets).map(([key, targets]) => {
              const label = key
                .replace("most_similar_to_", "Most similar to: ")
                .replace(/_/g, " ")
                .replace(/\b\w/g, l => l.toUpperCase());
              const tList = targets as SimilarTarget[];
              return (
                <div key={key}>
                  <p className="mb-2 text-sm font-semibold text-navy">{label}</p>
                  <div className="overflow-x-auto rounded-lg border border-slate-100">
                    <table className="min-w-full text-xs">
                      <thead className="bg-slate-50 text-slate-500">
                        <tr>
                          <th className="px-3 py-2 text-left">Player</th>
                          <th className="px-3 py-2 text-left">School</th>
                          <th className="px-2 py-2 text-center">Pos</th>
                          <th className="px-2 py-2 text-center" title="Illinois Fit Score (0-100)">IL Fit</th>
                          <th className="px-2 py-2 text-center" title="Transfer Translation Score (0-100)">Translation</th>
                        </tr>
                      </thead>
                      <tbody>
                        {tList.map((p) => (
                          <tr key={p.player_name} className="border-t border-slate-50 hover:bg-slate-50">
                            <td className="px-3 py-1.5 font-medium text-navy">{p.player_name}</td>
                            <td className="px-3 py-1.5 text-slate-500">{p.school}</td>
                            <td className="px-2 py-1.5 text-center text-slate-500">{p.position}</td>
                            <td className="px-2 py-1.5 text-center">{p.illinois_fit_score?.toFixed(0) ?? "—"}</td>
                            <td className="px-2 py-1.5 text-center">{p.transfer_success_score?.toFixed(0) ?? "—"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              );
            })}
          </div>
        )}
        <p className="mt-3 text-xs text-slate-400">Similarity computed via cosine distance on 12 statistical features. Prototype demo dataset.</p>
      </SectionCard>
    </div>
  );
}
