import numpy as np
import pandas as pd


NEED_WEIGHTS = {
    "Shooting":      {"three_pt_pct": 0.32, "ft_pct": 0.20, "true_shooting": 0.28, "usage_rate": 0.08, "minutes": 0.12},
    "Wing Defense":  {"steal_rate": 0.25, "block_rate": 0.14, "defensive_rating": -0.22, "height_inches": 0.14, "defensive_rebound_rate": 0.15, "minutes": 0.10},
    "Ball Handling": {"assist_rate": 0.34, "turnover_rate": -0.25, "usage_rate": 0.12, "ft_pct": 0.09, "minutes": 0.20},
    "Rebounding":    {"offensive_rebound_rate": 0.28, "defensive_rebound_rate": 0.34, "height_inches": 0.13, "block_rate": 0.10, "minutes": 0.15},
    "Rim Protection":{"block_rate": 0.38, "height_inches": 0.20, "defensive_rebound_rate": 0.17, "defensive_rating": -0.15, "minutes": 0.10},
    "Balanced":      {"true_shooting": 0.18, "assist_rate": 0.14, "defensive_rebound_rate": 0.13, "steal_rate": 0.13, "block_rate": 0.10, "minutes": 0.14, "prior_bpm": 0.18},
}

ROLE_MAP = {
    "G":  "rotation guard",
    "PG": "point guard",
    "SG": "shooting guard",
    "CG": "secondary creator",
    "W":  "3&D wing",
    "SF": "small forward",
    "F":  "versatile frontcourt piece",
    "PF": "power forward",
    "C":  "rim-running big",
}


def _normalize(series: pd.Series, inverse: bool = False) -> pd.Series:
    low, high = series.min(), series.max()
    if np.isclose(low, high):
        values = pd.Series(50.0, index=series.index, dtype=float)
    else:
        values = 100.0 * (series - low) / (high - low)
    return 100.0 - values if inverse else values


def add_scores(players: pd.DataFrame, need: str = "Balanced") -> pd.DataFrame:
    df = players.copy()

    # --- Transfer success score ---
    # Primary signal: calibrated GBM probability (AUC 0.896, temporal CV).
    # Secondary signal: stat-based proxy for players where the model is missing.
    if "ml_success_prob" in df.columns:
        # ML is the primary driver (80%), stat proxy adds 20% for stat context
        stat_proxy = (
            0.35 * _normalize(df["prior_bpm"])
            + 0.25 * _normalize(df["true_shooting"])
            + 0.15 * _normalize(df["usage_rate"])
            + 0.15 * _normalize(df["minutes"])
            + 0.10 * _normalize(df["assist_rate"])
        )
        df["transfer_success_score"] = (
            0.80 * df["ml_success_prob"]
            + 0.20 * stat_proxy
        ).clip(0, 100).round(1)
    else:
        df["transfer_success_score"] = (
            0.30 * _normalize(df["prior_bpm"])
            + 0.20 * _normalize(df["true_shooting"])
            + 0.15 * _normalize(df["usage_rate"])
            + 0.15 * _normalize(df["minutes"])
            + 0.10 * _normalize(df["assist_rate"])
            + 0.10 * _normalize(df["defensive_rebound_rate"] + df["offensive_rebound_rate"])
        ).round(1)

    # --- Risk score ---
    risk = (
        0.23 * _normalize(35 - df["minutes"])
        + 0.22 * _normalize(df["turnover_rate"])
        + 0.19 * _normalize(0.78 - df["ft_pct"])
        + 0.18 * _normalize(0.56 - df["true_shooting"])
        + 0.18 * _normalize(abs(df["usage_rate"] - 22))
    )
    df["risk_score"] = risk.clip(0, 100).round(1)

    # --- Illinois fit score ---
    weights = NEED_WEIGHTS.get(need, NEED_WEIGHTS["Balanced"])
    fit = pd.Series(0.0, index=df.index)
    total = 0.0
    for col, weight in weights.items():
        inverse = weight < 0
        fit += abs(weight) * _normalize(df[col], inverse=inverse)
        total += abs(weight)
    df["illinois_fit_score"] = (fit / total).clip(0, 100).round(1)

    # --- Derived ranks and composite score ---
    df["model_rank"] = df["transfer_success_score"].rank(ascending=False, method="min").astype(int)
    market_gap = (df["public_rank"] - df["model_rank"]).clip(lower=0)
    inefficiency = _normalize(market_gap)

    df["hidden_gem_score"] = (
        0.45 * df["transfer_success_score"]   # ML-driven success probability
        + 0.25 * df["illinois_fit_score"]      # Illinois-specific roster fit
        + 0.20 * inefficiency                  # market undervaluation
        - 0.10 * df["risk_score"]              # downside risk
    ).clip(0, 100).round(1)

    df["primary_skill"] = df.apply(primary_skill, axis=1)
    df["risk_level"] = pd.cut(df["risk_score"], bins=[-1, 34, 66, 101], labels=["Low", "Medium", "High"])
    return df.sort_values("hidden_gem_score", ascending=False).reset_index(drop=True)


def primary_skill(row: pd.Series) -> str:
    skill_scores = {
        "Shooting":    row["three_pt_pct"] * 65 + row["ft_pct"] * 35,
        "Playmaking":  row["assist_rate"] - row["turnover_rate"],
        "Defense":     row["steal_rate"] * 9 + row["block_rate"] * 5 + (110 - row["defensive_rating"]),
        "Rebounding":  row["offensive_rebound_rate"] + row["defensive_rebound_rate"],
        "Efficiency":  row["true_shooting"] * 100 + row["prior_bpm"],
    }
    return max(skill_scores, key=skill_scores.get)


def player_dimensions(row: pd.Series) -> dict:
    return {
        "Shooting":    round(min(100, row["three_pt_pct"] * 125 + row["ft_pct"] * 55), 1),
        "Playmaking":  round(min(100, row["assist_rate"] * 3.1 - row["turnover_rate"] * 1.5 + 50), 1),
        "Defense":     round(min(100, row["steal_rate"] * 8 + row["block_rate"] * 5 + (112 - row["defensive_rating"]) * 3), 1),
        "Rebounding":  round(min(100, (row["offensive_rebound_rate"] + row["defensive_rebound_rate"]) * 2.2), 1),
        "Efficiency":  round(min(100, row["true_shooting"] * 115 + row["prior_bpm"] * 2), 1),
        "Fit":         round(row.get("illinois_fit_score", 50), 1),
    }


def fit_impact(row: pd.Series) -> dict:
    return {
        "Spacing":       round((row["three_pt_pct"] - 0.33) * 80 + (row["ft_pct"] - 0.72) * 25, 1),
        "Defense":       round((108 - row["defensive_rating"]) * 0.7 + row["steal_rate"] * 0.8 + row["block_rate"] * 0.5, 1),
        "Rebounding":    round((row["offensive_rebound_rate"] + row["defensive_rebound_rate"] - 18) * 0.45, 1),
        "Ball Handling": round(row["assist_rate"] * 0.45 - row["turnover_rate"] * 0.55, 1),
        "Rim Protection":round(row["block_rate"] * 0.85 + (row["height_inches"] - 78) * 0.22, 1),
    }


def projected_role(row: pd.Series) -> str:
    base = ROLE_MAP.get(row["position"], "rotation piece")
    prob = row.get("ml_success_prob", row.get("transfer_success_score", 50))
    if prob >= 70:
        return f"starter-level {base}"
    if prob >= 40:
        return f"high-minute {base}"
    return f"developmental {base}"


def roster_grade(score: float) -> str:
    if score >= 92: return "A+"
    if score >= 87: return "A"
    if score >= 82: return "A-"
    if score >= 76: return "B+"
    if score >= 70: return "B"
    if score >= 64: return "B-"
    return "C"
