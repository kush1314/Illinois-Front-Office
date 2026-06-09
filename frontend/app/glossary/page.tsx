"use client";

import { SectionCard } from "@/components/section-card";

const TERMS: Array<{ term: string; short: string; detail: string; gmNote: string }> = [
  {
    term: "Transfer Translation Score (0-100)",
    short: "How likely current production carries to Big Ten rotation",
    detail: "Inputs: efficiency (TS%), prior BPM, usage rate, conference strength, rebounding, playmaking. Prototype model trained on synthetic NCAA-calibrated data.",
    gmNote: "Use as primary shortlist filter. 70+ = safe to proceed. Under 50 = needs strong film evidence. Not a guarantee of success.",
  },
  {
    term: "Illinois Fit Score (0-100)",
    short: "How well the player's profile matches Underwood's system",
    detail: "Weights: 3-point shooting (36.5% threshold), defensive rating, assist rate, usage efficiency. Tuned to Illinois's up-tempo, 3-heavy offense and perimeter switching defense.",
    gmNote: "65+ means the player checks the system boxes. Pair with Translation Score for Tier 1 candidates.",
  },
  {
    term: "Risk Score (0-100) — lower is safer",
    short: "Penalizes production warning signs",
    detail: "Penalizes: small sample size (under 20 games), high turnover rate (18%+), poor FT% (under 70%), low TS% (under 50%), extreme usage mismatch vs. expected Illinois role.",
    gmNote: "Under 35 = low risk. 35-55 = moderate — review role expectations. Over 55 = use only if upside justifies diligence investment.",
  },
  {
    term: "Hidden Gem Score (0-100)",
    short: "Production relative to market attention",
    detail: "Combines Translation Score, Illinois Fit, and Value Gap. High score means the model sees more value than the player's dataset rank suggests.",
    gmNote: "Does NOT mean the player is secretly elite. Means they may be undervalued relative to metrics. Film-verify before acting.",
  },
  {
    term: "Value Gap Score / Market Inefficiency Score (0-100)",
    short: "Gap between model rank and dataset rank",
    detail: "How much higher our scoring model ranks a player compared to where they appear in the prototype dataset's sequential rank field.",
    gmNote: "High value gap = Illinois can move before competing programs identify the same inefficiency. Time-sensitive.",
  },
  {
    term: "Dataset Rank (1-150)",
    short: "Prototype market attention field",
    detail: "A sequential rank in our prototype dataset (1 = highest-profile, 150 = lowest). NOT from ESPN, Rivals, On3, or any external scouting service. Used to model market inefficiency for demonstration.",
    gmNote: "Do NOT treat as an authoritative external ranking. It is a prototype field for demo purposes only.",
  },
  {
    term: "Projected BPM at Illinois",
    short: "Estimated box-score impact per 100 possessions",
    detail: "BPM (Box Plus/Minus) measures a player's contribution per 100 team possessions. 0 = average Big Ten starter. +2 = solid rotation. +4 = star. Negative = below-average role.",
    gmNote: "Useful for ceiling vs. floor sizing. Model trained on synthetic data — treat as directional, not definitive.",
  },
  {
    term: "Rotation Impact Score (0-100)",
    short: "Composite production ceiling estimate",
    detail: "Combines Translation Score, Projected BPM, and Illinois Fit Score into a single composite. 70+ = likely positive rotation contributor. 50-70 = quality depth. Under 50 = developmental.",
    gmNote: "Not a ranking of overall talent. A depth piece with perfect fit can outscore a raw prospect.",
  },
  {
    term: "BPM (Box Plus/Minus)",
    short: "Per-100-possession net impact estimate",
    detail: "Prior BPM (last season) is the single strongest predictor of future production in the scoring model. Positive = above average. Zero = average. Negative = below average.",
    gmNote: "A player with BPM +3 is a meaningful positive impact player. BPM -2 is a rotation liability. Context: college BPMs are higher than NBA equivalents.",
  },
  {
    term: "TS% (True Shooting Percentage)",
    short: "Most accurate single shooting efficiency metric",
    detail: "Points scored / (2 × (FGA + 0.44 × FTA)). Accounts for 2PT, 3PT, and free throws together. 55%+ = efficient. 60%+ = elite. Illinois threshold: 55%+ for perimeter players.",
    gmNote: "A guard with 58% TS% and 20% usage is a reliable offensive weapon. Below 50% with high usage = production concern.",
  },
  {
    term: "Usage Rate",
    short: "% of possessions used by the player on floor",
    detail: "Includes shots, free throw attempts, and turnovers. 20-25% = standard rotation. 25-30% = featured player. 30%+ = primary option. High usage at mid-major may not be sustainable at a major.",
    gmNote: "Risk factor: a 30% usage player moving from CUSA to Big Ten often sees role reduction. The Translation model accounts for this.",
  },
  {
    term: "Assist Rate / AST%",
    short: "% of teammate FGs assisted while on floor",
    detail: "Measures playmaking impact. Illinois wants guards at 16%+ assist rate (Underwood's system threshold for secondary creation).",
    gmNote: "A guard at 25% AST with under 15% TO rate is a high-value Illinois system fit.",
  },
  {
    term: "Defensive Rating",
    short: "Points allowed per 100 possessions when player is on floor",
    detail: "Lower = better defense. 95-100 = elite. 100-105 = average. 105+ = defensive liability. Illinois threshold: under 100.5 for perimeter players.",
    gmNote: "Important for switching scheme. A wing with 106 defensive rating needs film confirmation — may be team context, may be real.",
  },
  {
    term: "Conference Upgrade/Downgrade",
    short: "How much harder the new conference is vs. old one",
    detail: "Moving from CUSA to Big Ten is a major upgrade — model penalizes production translation. Moving from Big Ten to CUSA is a downgrade — model inflates projection. The translation score accounts for conference delta.",
    gmNote: "A player with +3 BPM in the Sun Belt might project to +1 BPM in the Big Ten. The model captures this discount.",
  },
];

export default function GlossaryPage(): JSX.Element {
  return (
    <div className="space-y-6">
      <SectionCard
        title="Metric Glossary"
        subtitle="Plain-English definitions for every score, label, and metric in this product."
      >
        <p className="text-sm text-slate-600">
          Every number in this tool has a specific meaning and interpretation. Use this page to understand
          what you are seeing, how to interpret high vs. low values, and what action each score should
          drive. Ask the chatbot &quot;what does [metric] mean?&quot; for instant explanations.
        </p>
      </SectionCard>

      <div className="space-y-3">
        {TERMS.map((t) => (
          <div key={t.term} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <h3 className="font-bold text-navy">{t.term}</h3>
              <span className="rounded-full bg-orange/10 px-3 py-0.5 text-[11px] font-semibold text-orange">
                {t.short}
              </span>
            </div>
            <div className="mt-3 grid gap-3 md:grid-cols-2">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">How it works</p>
                <p className="mt-1 text-sm text-slate-600">{t.detail}</p>
              </div>
              <div className="rounded-lg bg-navy/5 p-3">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-navy">GM take</p>
                <p className="mt-1 text-sm font-medium text-navy">{t.gmNote}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <SectionCard title="Prototype Dataset Disclaimer" subtitle="What this tool can and cannot claim">
        <div className="space-y-2 text-sm text-slate-700">
          <p><strong>Players:</strong> Synthetic demo profiles (not real current portal players). Calibrated to NCAA statistical distributions.</p>
          <p><strong>Model:</strong> Multi-model scoring system, trained on 3,000 synthetic profiles. Real methodology, synthetic training data.</p>
          <p><strong>Rankings:</strong> Dataset Rank is a prototype field, not from ESPN/Rivals/On3.</p>
          <p><strong>Roster:</strong> Sample Illinois baseline (June 2026). Verify against Illinois Athletics before citing.</p>
          <p><strong>Use case:</strong> Workflow prototype, methodology demonstration, and recruiting process design. Replace with real data before making actual recruiting decisions.</p>
        </div>
      </SectionCard>
    </div>
  );
}
