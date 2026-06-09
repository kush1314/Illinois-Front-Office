"""Scouting report generation.

model_explanation() uses SHAP values from the trained GBM to attribute each
player's success probability to specific features — replacing hand-coded if/else
rules with data-driven attributions. Falls back gracefully if SHAP is unavailable.
"""
from pathlib import Path

import numpy as np
import pandas as pd

from utils.scoring import fit_impact, player_dimensions, projected_role


_ROOT = Path(__file__).resolve().parents[1]
_MODELS_DIR = _ROOT / "models"

_FEATURE_LABELS = {
    "previous_bpm":      "prior BPM",
    "ts_pct":            "true shooting",
    "offensive_rating":  "offensive rating",
    "defensive_rating":  "defensive rating",
    "conf_upgrade":      "conference level change",
    "usage_rate":        "usage rate",
    "three_pt_pct":      "3-point percentage",
    "ft_pct":            "free-throw rate",
    "minutes":           "playing time",
    "assist_rate":       "assist rate",
    "def_rebound_rate":  "defensive rebound rate",
    "block_rate":        "block rate",
    "steal_rate":        "steal rate",
    "turnover_rate":     "turnover rate",
}

_FEATURE_RENAME_BACK = {
    "prior_bpm":               "previous_bpm",
    "true_shooting":           "ts_pct",
    "offensive_rebound_rate":  "off_rebound_rate",
    "defensive_rebound_rate":  "def_rebound_rate",
}


def _get_shap_values(row: pd.Series) -> list[tuple[str, float]]:
    """Return list of (feature_label, shap_value) sorted by absolute impact."""
    try:
        import joblib, shap

        model = joblib.load(_MODELS_DIR / "transfer_success_model.pkl")
        features = joblib.load(_MODELS_DIR / "model_features.pkl")

        # Map renamed columns back to training feature names
        raw = {}
        for feat in features:
            app_col = {v: k for k, v in _FEATURE_RENAME_BACK.items()}.get(feat, feat)
            raw_col = _FEATURE_RENAME_BACK.get(app_col, app_col)
            val = row.get(app_col, row.get(raw_col, np.nan))
            raw[feat] = float(val) if not pd.isna(val) else 0.0

        x = pd.DataFrame([raw])[features]

        # Extract the underlying GBM from the calibrated wrapper
        base = model.calibrated_classifiers_[0].estimator
        explainer = shap.TreeExplainer(base.named_steps["clf"])
        # Scale x the same way the pipeline does
        x_scaled = base.named_steps["scaler"].transform(x)
        shap_vals = explainer.shap_values(x_scaled)[0]  # class-1 (success) shap

        pairs = [(feat, sv) for feat, sv in zip(features, shap_vals)]
        pairs.sort(key=lambda p: abs(p[1]), reverse=True)
        return pairs
    except Exception:
        return []


def model_explanation(row: pd.Series) -> list[str]:
    """Return 3-4 data-driven bullets explaining why the model rates this player."""
    notes = []
    shap_pairs = _get_shap_values(row)

    if shap_pairs:
        # Show top 2 positive drivers, then 1 risk factor
        positives = [(f, sv) for f, sv in shap_pairs if sv > 0][:2]
        negatives = [(f, sv) for f, sv in shap_pairs if sv < 0][:1]
        for feat, sv in positives + negatives:
            positive = sv > 0
            app_col = {v: k for k, v in _FEATURE_RENAME_BACK.items()}.get(feat, feat)
            raw_col = _FEATURE_RENAME_BACK.get(app_col, app_col)
            val = row.get(app_col, row.get(raw_col, None))

            if feat == "previous_bpm" and val is not None:
                verb = "anchors" if positive else "caps"
                notes.append(f"Prior BPM of {val:.1f} {verb} the success probability — the model's strongest signal.")
            elif feat == "ts_pct" and val is not None:
                verb = "projects well" if positive else "is a concern"
                notes.append(f"{float(val):.1%} true shooting {verb} for scoring translation at the Big Ten level.")
            elif feat == "conf_upgrade" and val is not None:
                change = "upgrade" if float(val) > 0 else "downgrade" if float(val) < 0 else "lateral"
                verb = "boosts" if positive else "suppresses"
                notes.append(f"Conference {change} (Δ{float(val):+.2f}) {verb} the model's probability estimate.")
            elif feat == "offensive_rating" and val is not None:
                verb = "indicates efficient team fit" if positive else "flags team-context risk"
                notes.append(f"Offensive rating of {float(val):.0f} {verb}.")
            elif feat == "minutes" and val is not None:
                verb = "confirms an established role" if positive else "raises questions about role scalability"
                notes.append(f"{float(val):.0f} minutes last season {verb}.")
            elif feat == "three_pt_pct" and val is not None:
                verb = "adds spacing value" if positive else "is a drag on the projection"
                notes.append(f"{float(val):.1%} from three {verb} for Illinois's offensive system.")
            elif feat == "def_rebound_rate" and val is not None:
                verb = "strengthens" if positive else "limits"
                notes.append(f"Defensive rebounding ({float(val):.1f}%) {verb} the model's probability.")
            elif val is not None:
                label = _FEATURE_LABELS.get(feat, feat)
                verb = "contributes positively" if positive else "is a risk factor"
                notes.append(f"{label.title()} {verb} in the model's assessment.")
    else:
        # Stat-based fallback if SHAP fails
        dims = player_dimensions(row)
        strengths = sorted(dims.items(), key=lambda x: x[1], reverse=True)[:3]
        for label, _ in strengths:
            if label == "Shooting":
                notes.append(f"{row['three_pt_pct']:.1%} from three and {row['ft_pct']:.1%} at the line point to shooting translation.")
            elif label == "Playmaking":
                notes.append(f"{row['assist_rate']:.1f}% assist rate gives Illinois a real secondary creation option.")
            elif label == "Defense":
                notes.append(f"Defensive indicators: {row['steal_rate']:.1f}% steal rate, {row['block_rate']:.1f}% block rate, {row['defensive_rating']:.0f} defensive rating.")
            elif label == "Rebounding":
                notes.append(f"Rebounding profile: {row['offensive_rebound_rate']:.1f}% ORB + {row['defensive_rebound_rate']:.1f}% DRB.")
            elif label == "Efficiency":
                notes.append(f"Efficient production at {row['true_shooting']:.1%} true shooting.")

    if row.get("ml_success_prob") is not None:
        prob = float(row["ml_success_prob"])
        if prob >= 70:
            notes.append(f"Model confidence: {prob:.0f}% success probability — top tier for this portal class.")
        elif prob >= 40:
            notes.append(f"Model confidence: {prob:.0f}% success probability — above-average projection.")
        else:
            notes.append(f"Model confidence: {prob:.0f}% success probability — significant development risk.")

    return notes[:4]


def concern(row: pd.Series) -> str:
    if row["turnover_rate"] > 17:
        return "Turnover rate makes him risky as a primary initiator against Big Ten pressure."
    if row["three_pt_pct"] < 0.32 and row["position"] in ["G", "PG", "SG", "CG", "W"]:
        return "Perimeter shooting must translate for him to close games in smaller lineups."
    if row["defensive_rating"] > 105:
        return "Defensive tape should confirm whether the metrics are team-context noise or a real issue."
    if row["minutes"] < 21:
        return "Lower minutes sample means the staff should validate stamina and role scalability."
    if row.get("ml_success_prob", 50) < 30:
        return "Model flags elevated risk — prior BPM and efficiency metrics suggest limited upside at Big Ten level."
    return "No single red flag dominates, but role clarity will matter."


def usage(row: pd.Series) -> str:
    impacts = fit_impact(row)
    best = max(impacts, key=impacts.get)
    if best == "Spacing":
        return "Catch-and-shoot spacing, transition offense, and simple second-side reads."
    if best == "Ball Handling":
        return "Backup ball handling, early offense decisions, and late-clock secondary creation."
    if best == "Rim Protection":
        return "Drop coverage, weak-side rim protection, rim running, and offensive glass pressure."
    if best == "Rebounding":
        return "Lineup stabilizer who ends defensive possessions and creates extra shots."
    return "Defensive versatility, matchup flexibility, and low-maintenance offensive usage."


def scouting_snapshot(row: pd.Series) -> str:
    bullets = "\n".join(f"- {note}" for note in model_explanation(row))
    prob_line = ""
    if row.get("ml_success_prob") is not None:
        prob_line = f"\nML success probability: {row['ml_success_prob']:.0f}% (GBM classifier, AUC 0.896)\n"
    return (
        f"Recommendation: {row['player_name']} profiles as a {projected_role(row)} for Illinois.\n"
        f"{prob_line}\n"
        f"Why the model likes him:\n{bullets}\n\n"
        f"Best usage: {usage(row)}\n\n"
        f"Concern: {concern(row)}"
    )
