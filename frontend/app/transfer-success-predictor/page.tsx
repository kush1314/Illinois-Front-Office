"use client";

import { useEffect, useState } from "react";
import Plot from "@/components/plot";
import { SectionCard } from "@/components/section-card";
import { Player, apiGet, formatPct } from "@/lib/api";

type PlayersResponse = { items: Player[] };

type Prediction = {
  transfer_success_probability: number;
  future_bpm_prediction: number;
  rf_bpm_prediction: number | null;
  xgboost_bpm_prediction: number | null;
  neural_network_bpm_prediction: number | null;
  future_impact_score_prediction: number;
  feature_importance: Array<{ feature: string; importance: number }>;
};

type ModelPerformance = {
  holdout: {
    random_forest:  { r2: number; rmse: number; mae: number };
    xgboost:        { r2: number; rmse: number; mae: number } | null;
    neural_network: { r2: number; rmse: number; mae: number } | null;
    ensemble:       { r2: number; rmse: number; mae: number };
    classifier:     { roc_auc: number; accuracy: number };
  };
  cross_validation: {
    random_forest_r2: { mean: number; std: number };
  };
  training_rows:  number;
  feature_count:  number;
  model_stack:    string[];
};

function ScoreBar({ label, value, max = 100, color = "#13294B" }: { label: string; value: number; max?: number; color?: string }) {
  const pct = Math.min(100, (value / max) * 100);
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs text-slate-600">
        <span>{label}</span>
        <span className="font-semibold">{value.toFixed(1)}</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
        <div className="h-2 rounded-full" style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  );
}

function ModelCard({ title, data }: { title: string; data: { r2: number; rmse: number; mae: number } | null | undefined }) {
  if (!data) return null;
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="mb-2 text-sm font-bold text-navy">{title}</p>
      <div className="space-y-1.5 text-sm">
        <div className="flex justify-between">
          <span className="text-slate-500">R²</span>
          <span className="font-semibold text-navy">{data.r2.toFixed(3)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">RMSE</span>
          <span className="font-semibold">{data.rmse.toFixed(3)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">MAE</span>
          <span className="font-semibold">{data.mae.toFixed(3)}</span>
        </div>
      </div>
    </div>
  );
}

export default function TransferSuccessPredictorPage(): JSX.Element {
  const [players, setPlayers] = useState<Player[]>([]);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState("");
  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const [predLoading, setPredLoading] = useState(false);
  const [performance, setPerformance] = useState<ModelPerformance | null>(null);

  useEffect(() => {
    apiGet<PlayersResponse>("/players?limit=150").then((res) => {
      setPlayers(res.items);
      if (res.items.length > 0) setSelected(res.items[0].player_name);
    });
    apiGet<ModelPerformance>("/predict/model-performance").then(setPerformance).catch(() => {});
  }, []);

  useEffect(() => {
    if (!selected) return;
    setPredLoading(true);
    setPrediction(null);
    apiGet<Prediction>(`/predict/${encodeURIComponent(selected)}`)
      .then(setPrediction)
      .catch(() => {})
      .finally(() => setPredLoading(false));
  }, [selected]);

  const filtered = search
    ? players.filter((p) => p.player_name.toLowerCase().includes(search.toLowerCase()) || p.school.toLowerCase().includes(search.toLowerCase()))
    : players;

  const successColor =
    !prediction ? "#6B7280"
    : prediction.transfer_success_probability >= 70 ? "#16A34A"
    : prediction.transfer_success_probability >= 45 ? "#F59E0B"
    : "#DC2626";

  const currentPlayer = players.find((p) => p.player_name === selected);

  return (
    <div className="space-y-6">
      <SectionCard
        title="Transfer Success Predictor"
        subtitle="Prototype model — prototype scoring trained on synthetic data, NOT live recruiting predictions. Directional filter only."
      >
        <div className="mb-4 rounded border border-blue-200 bg-blue-50 p-3 text-xs text-blue-800">
          <strong>How to read this:</strong> Select any player to see how likely their current production is to carry over to a Big Ten rotation role.
          The model uses their shooting efficiency, scoring volume, passing, defense, and conference background.
          <strong> This is a research filter, not a recruiting guarantee.</strong> Use it to prioritize who to watch film on — then let the film confirm or deny the numbers.
        </div>
        <div className="flex flex-col gap-3 sm:flex-row">
          <input
            className="h-11 flex-1 rounded-lg border border-slate-300 px-3 text-sm outline-none focus:border-orange focus:ring-1 focus:ring-orange/30"
            placeholder="Search player or school…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <select
            className="h-11 w-full rounded-lg border border-slate-300 px-3 text-sm sm:w-72"
            value={selected}
            onChange={(e) => { setSelected(e.target.value); setSearch(""); }}
          >
            {filtered.map((p) => (
              <option key={p.player_name} value={p.player_name}>
                {p.player_name} — {p.school} ({p.position})
              </option>
            ))}
          </select>
        </div>
        {search && <p className="mt-1 text-xs text-slate-500">{filtered.length} players matching "{search}"</p>}
      </SectionCard>

      {/* Player context bar */}
      {currentPlayer && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
          {[
            { l: "Position", v: currentPlayer.position },
            { l: "School", v: currentPlayer.school },
            { l: "Conference", v: currentPlayer.conference },
            { l: "3PT%", v: formatPct(currentPlayer.three_pt_pct) },
            { l: "Def Rating", v: currentPlayer.defensive_rating?.toFixed(0) ?? "—" },
          ].map((s) => (
            <div key={s.l} className="rounded-lg border border-slate-200 bg-white px-4 py-3 text-center">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">{s.l}</p>
              <p className="mt-0.5 text-lg font-bold text-navy">{s.v}</p>
            </div>
          ))}
        </div>
      )}

      {/* ML predictions */}
      {predLoading && (
        <div className="flex h-32 items-center justify-center rounded-xl border border-slate-200 bg-white">
          <p className="text-sm text-slate-400">Running predictions…</p>
        </div>
      )}

      {prediction && !predLoading && (
        <>
          <div className="grid gap-4 md:grid-cols-3">
            <SectionCard title="Transfer Translation Score">
              <p className="text-5xl font-extrabold" style={{ color: successColor }}>
                {prediction.transfer_success_probability.toFixed(0)}/100
              </p>
              <p className="mt-1 text-xs text-slate-500">
                {prediction.transfer_success_probability >= 70 ? "Strong: production likely carries to a Big Ten rotation role" :
                 prediction.transfer_success_probability >= 45 ? "Moderate: confirm role and competition level on film" :
                 "Below average: meaningful production risk at the Big Ten level"}
              </p>
            </SectionCard>
            <SectionCard title="Projected BPM at Illinois">
              <p className={`text-5xl font-extrabold ${prediction.future_bpm_prediction >= 0 ? "text-green-600" : "text-red-500"}`}>
                {prediction.future_bpm_prediction >= 0 ? "+" : ""}{prediction.future_bpm_prediction.toFixed(1)}
              </p>
              <p className="mt-1 text-xs text-slate-500">
                Box Plus/Minus per 100 possessions estimate. 0 = average Big Ten starter. +2 = solid rotation contributor. Negative = production risk.
              </p>
            </SectionCard>
            <SectionCard title="Rotation Impact Score">
              <p className="text-5xl font-extrabold text-navy">{prediction.future_impact_score_prediction.toFixed(0)}/100</p>
              <p className="mt-1 text-xs text-slate-500">Composite of Translation Score + Projected BPM + Illinois Fit. 70+ = likely rotation contributor.</p>
            </SectionCard>
          </div>

          {/* Per-model breakdown */}
          <SectionCard title="Scoring Model Breakdown" subtitle="How each model in the system voted">
            <div className="space-y-3">
              <ScoreBar label="Model 1 BPM" value={prediction.rf_bpm_prediction ?? 0} max={8} color="#13294B" />
              <ScoreBar label="Model 2 BPM" value={prediction.xgboost_bpm_prediction ?? 0} max={8} color="#1e3f72" />
              <ScoreBar label="Model 3 BPM" value={prediction.neural_network_bpm_prediction ?? 0} max={8} color="#FF5F05" />
              <ScoreBar label="Combined score (weighted avg)" value={prediction.future_bpm_prediction} max={8} color="#16A34A" />
            </div>
            <p className="mt-3 text-xs text-slate-400">Scoring weights: Model 2 — 45% · Model 1 — 35% · Model 3 — 20%</p>
          </SectionCard>

          {/* Feature importance */}
          {prediction.feature_importance.length > 0 && (
            <SectionCard title="What drove this prediction" subtitle="Which stats had the biggest influence on this player's score">
              <Plot
                data={[{
                  x: prediction.feature_importance.map((f) => f.importance),
                  y: prediction.feature_importance.map((f) => f.feature.replace(/_/g, " ")),
                  type: "bar",
                  orientation: "h",
                  marker: { color: prediction.feature_importance.map((_, i) => i === 0 ? "#FF5F05" : "#13294B") },
                }]}
                layout={{
                  paper_bgcolor: "rgba(0,0,0,0)",
                  plot_bgcolor: "rgba(0,0,0,0)",
                  xaxis: { title: "Importance", gridcolor: "#f1f5f9" },
                  margin: { l: 150, r: 20, t: 10, b: 40 },
                  height: 280,
                }}
                style={{ width: "100%", height: 280 }}
                config={{ displayModeBar: false }}
              />
              <p className="mt-2 text-xs text-slate-400">
                Prior BPM is typically the strongest predictor — high-quality players tend to remain high-quality after transferring.
                Conference upgrade penalizes players moving to harder conferences.
              </p>
            </SectionCard>
          )}
        </>
      )}

      {/* Model performance */}
      {performance && (
        <SectionCard
          title="Scoring System Performance"
          subtitle={`Trained on ${performance.training_rows.toLocaleString()} historical transfers · 3-model scoring system`}
        >
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
            <ModelCard title="Model 1" data={performance.holdout.random_forest} />
            <ModelCard title="Model 2" data={performance.holdout.xgboost} />
            <ModelCard title="Model 3" data={performance.holdout.neural_network} />
            <ModelCard title="Combined Score" data={performance.holdout.ensemble} />
          </div>

          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="mb-2 text-sm font-bold text-navy">How accurate is the model?</p>
              <p className="text-sm text-slate-600">
                The model correctly separates players likely to succeed from likely busts{" "}
                <strong>{(performance.holdout.classifier.roc_auc * 100).toFixed(0)}% of the time</strong>{" "}
                on held-out data (players it never trained on).
                That&apos;s significantly better than a coin flip, but not perfect — real recruiting involves
                factors no stat can capture (character, coachability, injury history, NIL).
              </p>
              <p className="mt-2 text-xs text-slate-400">
                Technical note: ROC-AUC = {performance.holdout.classifier.roc_auc.toFixed(3)} | Accuracy = {(performance.holdout.classifier.accuracy * 100).toFixed(1)}%
              </p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="mb-2 text-sm font-bold text-navy">Is it consistent?</p>
              <p className="text-sm text-slate-600">
                Tested across 5 different train/test splits, the model performs consistently
                (R² = {performance.cross_validation.random_forest_r2.mean.toFixed(2)} ± {performance.cross_validation.random_forest_r2.std.toFixed(2)}).
                Low variation means it&apos;s not just getting lucky on one specific test set.
              </p>
              <p className="mt-2 text-xs text-slate-400">
                Training data: {performance.training_rows.toLocaleString()} synthetic profiles calibrated to NCAA distributions.
              </p>
            </div>
          </div>
        </SectionCard>
      )}
    </div>
  );
}
