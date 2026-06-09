export type Player = {
  player_name: string;
  school: string;
  conference: string;
  position: string;
  class: string;
  height?: string;
  height_inches?: number;
  weight?: number;
  three_pt_pct: number;
  ft_pct?: number;
  ts_pct: number;
  offensive_rating?: number;
  defensive_rating: number;
  usage_rate?: number;
  assist_rate?: number;
  turnover_rate?: number;
  steal_rate?: number;
  block_rate?: number;
  off_rebound_rate?: number;
  def_rebound_rate?: number;
  bpm?: number;
  ppg?: number;
  rpg?: number;
  apg?: number;
  minutes?: number;
  games?: number;
  public_transfer_rank: number;
  transfer_success_score: number;
  illinois_fit_score: number;
  risk_score: number;
  hidden_gem_score: number;
  market_inefficiency_score: number;
  projected_impact_score: number;
  predicted_bpm?: number;
  archetype: string;
};

export type NavigationAction = {
  label: string;
  path: string;
  reason?: string;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api";

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function formatPct(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}
