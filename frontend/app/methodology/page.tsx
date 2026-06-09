"use client";

import { useEffect, useState } from "react";
import { SectionCard } from "@/components/section-card";
import Plot from "@/components/plot";
import { apiGet } from "@/lib/api";

type ModelPerf = {
  holdout: {
    random_forest:  { r2: number; rmse: number; mae: number };
    xgboost:        { r2: number; rmse: number; mae: number } | null;
    ensemble:       { r2: number; rmse: number; mae: number };
    classifier:     { roc_auc: number; accuracy: number };
  };
  cross_validation: { random_forest_r2: { mean: number; std: number } };
  training_rows: number;
  model_stack: string[];
};

function InfoBox({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
      <p className="mb-1.5 text-xs font-bold uppercase tracking-wider text-navy">{title}</p>
      <div className="text-sm leading-relaxed text-slate-700">{children}</div>
    </div>
  );
}

function MetricRow({ label, value, what, gmTake }: { label: string; value: string; what: string; gmTake: string }) {
  return (
    <div className="border-b border-slate-100 pb-3 last:border-0 last:pb-0">
      <div className="flex items-baseline justify-between">
        <span className="text-sm font-semibold text-navy">{label}</span>
        <span className="text-sm font-bold text-orange">{value}</span>
      </div>
      <p className="mt-0.5 text-xs text-slate-500">{what}</p>
      <p className="mt-0.5 text-xs font-medium text-slate-700">GM take: {gmTake}</p>
    </div>
  );
}

export default function MethodologyPage(): JSX.Element {
  const [perf, setPerf] = useState<ModelPerf | null>(null);

  useEffect(() => {
    apiGet<ModelPerf>("/predict/model-performance").then(setPerf).catch(() => {});
  }, []);

  return (
    <div className="space-y-6">
      {/* Hero */}
      <SectionCard
        title="Methodology & About the Data"
        subtitle="What this product does, what data it uses, what the model claims, and what it does not claim."
      >
        <div className="rounded-lg border border-orange/30 bg-orange/5 p-4 text-sm text-slate-700">
          <p className="font-semibold text-orange">Honesty first</p>
          <p className="mt-1">
            This is a <strong>working prototype</strong>. The scoring architecture, logic, workflows, and UI are real.
            The player dataset is a <strong>synthetic demo sample</strong> of 150 profiles calibrated to NCAA-level statistical
            distributions — not live portal data. Use this tool to understand the methodology and interface; replace the
            dataset with a real portal feed before making actual recruiting decisions.
          </p>
        </div>
      </SectionCard>

      {/* Data section */}
      <SectionCard title="About the Data" subtitle="What's in the dataset and where it comes from">
        <div className="grid gap-4 md:grid-cols-2">
          <InfoBox title="Player Dataset">
            <p><strong>150 synthetic portal target profiles</strong> calibrated to match NCAA D1 statistical distributions.</p>
            <p className="mt-2">Includes: position, school, conference, height, class, PPG/RPG/APG, TS%, 3PT%, usage, BPM, defensive rating, assist rate, turnover rate, rebounding rates.</p>
            <p className="mt-2 font-medium text-orange">These are NOT real current portal players. Names, schools, and stats are illustrative. Do not use for actual recruiting decisions.</p>
          </InfoBox>
          <InfoBox title="Training Data">
            <p><strong>3,000 synthetic transfer outcome profiles</strong> calibrated to match real NCAA transfer statistical patterns.</p>
            <p className="mt-2">Labels include: prior BPM, future BPM, conference strength delta, usage, efficiency, and a binary success label (BPM ≥ 0 at destination).</p>
            <p className="mt-2 font-medium text-slate-500">This is NOT a dataset of verified real-world transfer outcomes with documented sourcing. It is synthetic training data for prototype demonstration.</p>
          </InfoBox>
          <InfoBox title="Illinois Roster">
            <p>Sample roster based on publicly available Illinois Athletics information (as of June 2026). Includes key returners: Stojakovic, Z. Ivisic, T. Ivisic, Wagler, Vaaks.</p>
            <p className="mt-2 font-medium text-slate-500">Verify against official Illinois Athletics before citing in any real recruiting context.</p>
          </InfoBox>
          <InfoBox title="Live Data Infrastructure">
            <p>Scrapers for BartTorvik and Sports Reference are included in the codebase. In production, these would pull real portal entries and advanced stats.</p>
            <p className="mt-2">Current status: live scraping blocked by Cloudflare (BartTorvik) and JavaScript rendering (Sports Reference). Synthetic fallback is used instead.</p>
          </InfoBox>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-3 text-center">
          {[
            { v: "150", l: "Portal profiles", s: "synthetic prototype dataset" },
            { v: "3,000", l: "Training samples", s: "synthetic, NCAA-calibrated" },
            { v: "14", l: "Roster players", s: "June 2026 sample baseline" },
          ].map(s => (
            <div key={s.l} className="rounded-lg border border-slate-200 p-3">
              <p className="text-2xl font-extrabold text-navy">{s.v}</p>
              <p className="text-xs font-semibold text-orange">{s.l}</p>
              <p className="text-[10px] text-slate-400">{s.s}</p>
            </div>
          ))}
        </div>
      </SectionCard>

      {/* Score definitions */}
      <SectionCard title="Score Definitions" subtitle="What every metric means and how to use it">
        <div className="space-y-4">
          {[
            {
              name: "Transfer Translation Score (0-100)",
              how: "Estimates how likely a player's current production profile will carry over to a Big Ten rotation role. Inputs: efficiency (TS%), prior BPM, usage, conference strength, rebounding, playmaking.",
              interp: "70+ = strong translation likely. 50-70 = moderate — confirm role and competition level on film. Under 50 = production risk.",
              action: "Use as the primary filter for shortlisting targets. 65+ is your starting threshold.",
            },
            {
              name: "Illinois Fit Score (0-100)",
              how: "How well the player's skill profile matches Brad Underwood's system requirements: 3-point shooting (36.5% threshold), perimeter switching defense, playmaking, positional versatility.",
              interp: "65+ = strong system match. 50-65 = fits some needs. Under 50 = system mismatch unless specific role available.",
              action: "Cross-reference with Translation Score. High Fit + High Translation = Tier 1 target.",
            },
            {
              name: "Risk Score (0-100) — lower is safer",
              how: "Penalizes: small sample size (under 20 games), high turnover rate (18%+), poor FT% (under 70%), inefficient scoring (TS% under 50%), extreme usage mismatch vs. expected Illinois role.",
              interp: "Under 35 = low risk. 35-55 = moderate — review role expectations. Over 55 = elevated risk.",
              action: "Set a max risk of 55 for safe-floor targets. High-ceiling bets can go to 65 with strong Film/upside evidence.",
            },
            {
              name: "Hidden Gem Score (0-100)",
              how: "Identifies players where our scoring model ranks them significantly higher than their dataset rank. High score = strong production relative to market attention level.",
              interp: "Does NOT mean the player is secretly elite. Means the metrics suggest they are undervalued relative to their dataset rank. Verify with film.",
              action: "Act on high Hidden Gem players before competing programs identify the same inefficiency. Typical window: days, not weeks.",
            },
            {
              name: "Dataset Rank (1-150)",
              how: "A sequential rank field in our prototype dataset representing approximate consensus market attention. Rank #1 = highest-profile in dataset, #150 = lowest.",
              interp: "This is NOT from ESPN, Rivals, On3, or any live recruiting service. It is a prototype field.",
              action: "Use only for the market inefficiency calculation. Do not treat as an authoritative external ranking.",
            },
            {
              name: "Projected BPM at Illinois",
              how: "Multi-model scoring estimate of the player's Box Plus/Minus per 100 possessions in an Illinois-level rotation. BPM: 0 = average starter, +2 = solid rotation, +4 = potential star.",
              interp: "Positive = above-average rotation impact. Negative = depth role or mismatch. Trained on synthetic data — treat as directional.",
              action: "Use alongside Translation Score to estimate ceiling vs. floor.",
            },
          ].map(s => (
            <div key={s.name} className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="font-bold text-navy">{s.name}</p>
              <div className="mt-2 grid gap-2 md:grid-cols-3">
                <div>
                  <p className="text-[10px] font-semibold uppercase text-slate-400">How it's calculated</p>
                  <p className="mt-0.5 text-xs text-slate-600">{s.how}</p>
                </div>
                <div>
                  <p className="text-[10px] font-semibold uppercase text-slate-400">How to interpret</p>
                  <p className="mt-0.5 text-xs text-slate-600">{s.interp}</p>
                </div>
                <div>
                  <p className="text-[10px] font-semibold uppercase text-slate-400">Staff action</p>
                  <p className="mt-0.5 text-xs font-medium text-navy">{s.action}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </SectionCard>

      {/* Model performance */}
      {perf && (
        <SectionCard title="Scoring Model Performance" subtitle="What the model predicts, how it was validated, and how to interpret the numbers">
          <div className="mb-4 rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
            <p className="font-semibold text-navy">What the model predicts</p>
            <p className="mt-1">
              The ensemble predicts two things: (1) a player&apos;s future BPM (Box Plus/Minus) at their new school —
              a continuous regression target — and (2) whether the transfer will be &quot;successful&quot; (BPM ≥ 0 at destination) —
              a binary classification target. The Transfer Translation Score is derived from the classifier probability.
            </p>
            <p className="mt-2 font-medium text-orange">
              Important: trained on 3,000 synthetic profiles. Metrics below reflect performance on synthetic data,
              not real-world validated outcomes. Treat as a structural prototype, not a live prediction system.
            </p>
          </div>

          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="text-xs font-bold uppercase text-slate-400">Regression — Ensemble BPM</p>
              <div className="mt-2 space-y-2">
                <MetricRow
                  label="R² (Holdout)"
                  value={perf.holdout.ensemble.r2.toFixed(3)}
                  what="How much variation in future BPM the model explains (0-1 scale, higher=better)"
                  gmTake={perf.holdout.ensemble.r2 > 0.5 ? "Model captures most of the predictable signal — useful directional filter." : "Moderate explanatory power — use alongside film, not instead of it."}
                />
                <MetricRow
                  label="RMSE"
                  value={`±${perf.holdout.ensemble.rmse.toFixed(2)} BPM`}
                  what="Average miss size in BPM units — typical error on any single player prediction"
                  gmTake={`Predictions are typically within ±${perf.holdout.ensemble.rmse.toFixed(1)} BPM. Use for direction (positive/negative), not precision.`}
                />
              </div>
            </div>

            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="text-xs font-bold uppercase text-slate-400">Classifier — Success/Bust</p>
              <div className="mt-2 space-y-2">
                <MetricRow
                  label="ROC-AUC"
                  value={perf.holdout.classifier.roc_auc.toFixed(3)}
                  what="How well the model separates successful transfers (BPM ≥ 0) from busts (0-1 scale, 0.5=random, 1.0=perfect)"
                  gmTake={perf.holdout.classifier.roc_auc > 0.85 ? "Strong separation — the model is reliably distinguishing likely contributors from production risks." : "Moderate AUC — use alongside other filters."}
                />
                <MetricRow
                  label="Accuracy"
                  value={`${(perf.holdout.classifier.accuracy * 100).toFixed(0)}%`}
                  what="Correct predictions on held-out data (success vs. bust) — note: imbalanced classes (~24% success rate)"
                  gmTake="Higher accuracy matters less than AUC here due to class imbalance."
                />
              </div>
            </div>

            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="text-xs font-bold uppercase text-slate-400">Cross-Validation</p>
              <div className="mt-2 space-y-2">
                <MetricRow
                  label="5-Fold CV R²"
                  value={`${perf.cross_validation.random_forest_r2.mean.toFixed(3)} ±${perf.cross_validation.random_forest_r2.std.toFixed(3)}`}
                  what="Held-out R² across 5 different train/test splits — tests for overfitting"
                  gmTake={`Low std (±${perf.cross_validation.random_forest_r2.std.toFixed(3)}) means model is stable, not just fitting one lucky split.`}
                />
                <MetricRow
                  label="Training rows"
                  value={perf.training_rows.toLocaleString()}
                  what="Size of training set (synthetic profiles calibrated to NCAA distributions)"
                  gmTake="Adequate for prototype. A production model would use 10,000+ real labeled transfer outcomes."
                />
              </div>
            </div>
          </div>

          <div className="mt-4 rounded-lg border border-green-200 bg-green-50 p-4 text-sm">
            <p className="font-semibold text-green-800">How a GM should use these metrics</p>
            <p className="mt-1 text-green-700">
              AUC 0.88 means the classifier correctly ranks likely contributors above likely busts ~88% of the time
              in cross-validation. That&apos;s a useful filter for reducing a 150-player portal to a 15-20 player shortlist.
              It is NOT a guarantee — a player at 85% Translation Score still has a meaningful chance of underperforming.
              Always pair the model with film, coach context, medical review, and NIL/role fit conversations.
            </p>
          </div>
        </SectionCard>
      )}

      {/* Action guide */}
      <SectionCard title="How to Use This Tool" subtitle="Recommended workflow for Illinois basketball staff">
        <div className="grid gap-3 md:grid-cols-2">
          {[
            { step: "1", title: "Start with a roster need", body: "Use the Roster Builder or ask the chatbot: 'What does Illinois need most in the portal?' The tool will identify positional gaps and suggest target types." },
            { step: "2", title: "Run the recruiting board", body: "Open Recruiting Center → filter by position and risk. Sort by Illinois Fit Score to find system-specific fits. Target Tier 1 (Fit ≥65, Risk <40) for immediate contact." },
            { step: "3", title: "Validate with the scoring model", body: "Open Transfer Success Predictor for any target. Review Translation Score, Projected BPM, and what drove the prediction. Anything below 55 Translation warrants extra film diligence." },
            { step: "4", title: "Identify hidden value", body: "Open Hidden Gem Lab. Focus on players with high Value Gap scores — model ranks them higher than dataset rank. These are your competitive advantage targets." },
            { step: "5", title: "Generate scouting reports", body: "Open Scouting Center for any player. Reports include strengths, weaknesses, Illinois fit verdict, and PDF export for staff distribution." },
            { step: "6", title: "Remember what this can't do", body: "The tool cannot assess NIL, character, coachability, medical history, family situation, academic eligibility, or scheme execution quality. Film and recruiting calls remain essential." },
          ].map(s => (
            <div key={s.step} className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="flex items-start gap-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-orange text-[11px] font-bold text-white">{s.step}</span>
                <div>
                  <p className="font-semibold text-navy">{s.title}</p>
                  <p className="mt-0.5 text-xs text-slate-600">{s.body}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </SectionCard>
    </div>
  );
}
