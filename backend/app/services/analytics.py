from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler


FIT_WEIGHTS = {
    "shooting": {"three_pt_pct": 0.28, "ft_pct": 0.18, "ts_pct": 0.2, "offensive_rating": 0.14, "usage_rate": 0.2},
    "defense": {"steal_rate": 0.18, "block_rate": 0.2, "defensive_rating": -0.28, "def_rebound_rate": 0.2, "height_inches": 0.14},
    "playmaking": {"assist_rate": 0.36, "turnover_rate": -0.28, "usage_rate": 0.18, "minutes": 0.18},
    "balanced": {"ts_pct": 0.18, "three_pt_pct": 0.14, "assist_rate": 0.16, "def_rebound_rate": 0.14, "steal_rate": 0.12, "previous_bpm": 0.26},
}

SIMILARITY_FEATURES = [
    "height_inches",
    "weight",
    "usage_rate",
    "ts_pct",
    "three_pt_pct",
    "assist_rate",
    "turnover_rate",
    "off_rebound_rate",
    "def_rebound_rate",
    "steal_rate",
    "block_rate",
    "minutes",
]

ARCTYPES = {
    0: "Two-Way Wing",
    1: "Primary Creator",
    2: "Stretch Big",
    3: "Rim Protector",
    4: "Microwave Scorer",
}


@dataclass
class TeamIdentity:
    label: str
    summary: str


def height_to_inches(height: str) -> int:
    feet, inches = height.split("-")
    return int(feet) * 12 + int(inches)


def normalize(series: pd.Series, inverse: bool = False) -> pd.Series:
    low, high = series.min(), series.max()
    if math.isclose(low, high):
        values = pd.Series(50.0, index=series.index)
    else:
        values = 100 * (series - low) / (high - low)
    if inverse:
        values = 100 - values
    return values.clip(0, 100)


def add_core_scores(players: pd.DataFrame, fit_profile: str = "balanced") -> pd.DataFrame:
    """
    Compute all player scores.

    transfer_success_score and projected_impact_score are generated from
    the trained ML ensemble (RF + XGBoost + MLP) when the model is available.
    Everything else falls back to interpretable formulas so the app always works.
    """
    df = players.copy()
    if "height_inches" not in df.columns:
        if "height" in df.columns:
            df["height_inches"] = df["height"].map(
                lambda h: height_to_inches(h) if isinstance(h, str) and "-" in str(h) else 75
            )
        else:
            df["height_inches"] = 75

    # ── ML-predicted transfer success & impact ────────────────────────────────
    # Try the trained RF+XGB+MLP ensemble first; fall back to formula if not ready.
    # Vectorized: predict all players at once for performance.
    try:
        from app.services.ml_registry import get_pipeline
        from app.services.ml import FEATURES, FEATURES_LEGACY

        pipeline = get_pipeline()
        if pipeline.is_trained():
            feat_cols = FEATURES if all(f in df.columns for f in FEATURES) else FEATURES_LEGACY
            feat_cols = [f for f in feat_cols if f in df.columns]
            X = df[feat_cols].fillna(df[feat_cols].median())

            # Predict all rows at once (vectorized, much faster than row-by-row)
            models = pipeline.models
            rf_probs  = models.rf_cls.predict_proba(X)[:, 1]
            mlp_probs = models.mlp_cls.predict_proba(X)[:, 1]
            success_probs = (0.55 * rf_probs + 0.45 * mlp_probs) * 100

            rf_bpm  = models.rf_reg.predict(X)
            mlp_bpm = models.mlp_reg.predict(X)
            xgb_bpm = models.xgb_reg.predict(X) if models.xgb_reg is not None else rf_bpm
            ens_bpm = 0.45 * xgb_bpm + 0.35 * rf_bpm + 0.20 * mlp_bpm

            df["transfer_success_score"] = success_probs.round(2)
            df["predicted_bpm"]          = ens_bpm.round(3)
            df["projected_impact_score"] = (
                (50 + ens_bpm * 6 + success_probs * 0.10).clip(0, 99)
            ).round(2)
            use_ml = True
        else:
            use_ml = False
    except Exception:
        use_ml = False

    if not use_ml:
        # Formula fallback (always interpretable)
        success = (
            0.28 * normalize(df.get("previous_bpm", pd.Series(0, index=df.index)))
            + 0.18 * normalize(df.get("ts_pct", pd.Series(0.5, index=df.index)))
            + 0.12 * normalize(df.get("usage_rate", pd.Series(20, index=df.index)))
            + 0.15 * normalize(df.get("minutes", pd.Series(500, index=df.index)))
            + 0.15 * normalize(df.get("assist_rate", pd.Series(15, index=df.index)))
            + 0.12 * normalize(
                df.get("def_rebound_rate", pd.Series(15, index=df.index))
                + df.get("off_rebound_rate", pd.Series(5, index=df.index))
            )
        )
        if "future_bpm" in df.columns:
            success = 0.72 * success + 0.28 * normalize(df["future_bpm"])
        df["transfer_success_score"] = success.round(2)
        df["projected_impact_score"] = (
            0.45 * df["transfer_success_score"]
            + 0.35 * normalize(df.get("future_bpm", pd.Series(0, index=df.index)))
            + 0.2  * normalize(df.get("offensive_rating", pd.Series(100, index=df.index)))
        ).clip(0, 100).round(2)

    # ── Risk score (formula — interpretable by design) ─────────────────────
    risk = (
        0.20 * normalize(36 - df.get("minutes",      pd.Series(20, index=df.index)).clip(upper=36))
        + 0.24 * normalize(df.get("turnover_rate",   pd.Series(15, index=df.index)))
        + 0.19 * normalize(0.77 - df.get("ft_pct",   pd.Series(0.70, index=df.index)))
        + 0.20 * normalize(0.56 - df.get("ts_pct",   pd.Series(0.50, index=df.index)))
        + 0.17 * normalize(abs(df.get("usage_rate",  pd.Series(20, index=df.index)) - 22))
    )
    df["risk_score"] = risk.round(2)

    # ── Illinois fit score (formula — encodes coaching staff priorities) ───
    weights = FIT_WEIGHTS.get(fit_profile, FIT_WEIGHTS["balanced"])
    fit = pd.Series(0.0, index=df.index)
    total = 0.0
    for col, weight in weights.items():
        if col in df.columns:
            fit += abs(weight) * normalize(df[col], inverse=weight < 0)
            total += abs(weight)
    df["illinois_fit_score"] = ((fit / total) if total > 0 else fit).round(2)

    # ── Market inefficiency (model rank vs public rank gap) ────────────────
    if "public_transfer_rank" not in df.columns:
        df["public_transfer_rank"] = range(1, len(df) + 1)
    predicted_rank = df["transfer_success_score"].rank(ascending=False, method="dense")
    market_gap = (df["public_transfer_rank"] - predicted_rank).clip(lower=0)
    df["market_inefficiency_score"] = normalize(market_gap).round(2)

    # ── Hidden gem score (combines all signals) ────────────────────────────
    df["hidden_gem_score"] = (
        0.38 * df["transfer_success_score"]
        + 0.28 * df["illinois_fit_score"]
        + 0.24 * df["market_inefficiency_score"]
        - 0.10 * df["risk_score"]
    ).clip(0, 100).round(2)

    return df


def add_archetypes(players: pd.DataFrame) -> pd.DataFrame:
    df = players.copy()
    feats = ["usage_rate", "assist_rate", "three_pt_pct", "block_rate", "steal_rate", "height_inches", "off_rebound_rate"]
    feat_df = df[feats].fillna(df[feats].median())
    scaled = StandardScaler().fit_transform(feat_df)
    clusters = KMeans(n_clusters=5, random_state=42, n_init=20).fit_predict(scaled)
    df["archetype_cluster"] = clusters
    df["archetype"] = df["archetype_cluster"].map(lambda c: ARCTYPES.get(int(c), "Rotation Piece"))
    return df


def rank_targets(
    players: pd.DataFrame,
    position: str | None = None,
    min_height: int | None = None,
    conference: str | None = None,
    max_risk: float = 100,
    min_shooting: float = 0.0,
    min_defense: float = 0.0,
    min_rebounding: float = 0.0,
    min_playmaking: float = 0.0,
) -> pd.DataFrame:
    board = players.copy()

    if position and position != "Any":
        board = board[board["position"] == position]
    if min_height:
        board = board[board["height_inches"] >= min_height]
    if conference and conference != "Any":
        board = board[board["conference"] == conference]

    board = board[board["risk_score"] <= max_risk]
    board = board[board["three_pt_pct"] >= min_shooting]
    board = board[board["defensive_rating"] <= (120 - min_defense * 0.3)]
    board = board[board["def_rebound_rate"] >= min_rebounding * 0.2]
    board = board[board["assist_rate"] >= min_playmaking * 0.2]

    board = board.sort_values(["hidden_gem_score", "illinois_fit_score"], ascending=False)
    return board.head(25)


def compute_similarity(players: pd.DataFrame, player_name: str, top_n: int = 5) -> pd.DataFrame:
    df = players.copy()
    feature_df = df[SIMILARITY_FEATURES].fillna(df[SIMILARITY_FEATURES].median())
    scaled = StandardScaler().fit_transform(feature_df)
    idx = df.index[df["player_name"] == player_name]
    if len(idx) == 0:
        return pd.DataFrame()

    sims = cosine_similarity([scaled[idx[0]]], scaled)[0]
    df["similarity"] = sims
    return df[df["player_name"] != player_name].sort_values("similarity", ascending=False).head(top_n)


def roster_outcomes(players: pd.DataFrame) -> dict[str, float | str]:
    """
    Compute real projected basketball statistics for a hypothetical roster.
    All numbers are explained in basketball terms, not ML terms.
    """
    n = max(len(players), 1)

    # ── Real projected stats (calculated from actual player data) ────────────
    # Points per game: weighted by usage rate (higher usage = more shots taken)
    total_usage = players["usage_rate"].sum()
    if total_usage > 0:
        ppg_projected = float((players["ppg"] * players["usage_rate"]).sum() / total_usage * (n / 5))
    else:
        ppg_projected = float(players["ppg"].mean() * n / 5)
    ppg_projected = round(min(ppg_projected, 95.0), 1)

    # Rebounds per game: sum of individual rebound contributions (scaled to 5-player team)
    orpg_projected = round(float(players["off_rebound_rate"].mean() / 100 * 67 * 0.5), 1)
    drpg_projected = round(float(players["def_rebound_rate"].mean() / 100 * 67 * 0.5), 1)
    rpg_projected  = round(orpg_projected + drpg_projected, 1)

    # Assists per game: from assist rate (% of made FGs that were assisted)
    apg_projected = round(float(players["assist_rate"].mean() / 100 * ppg_projected / 2.1), 1)

    # Team 3-point shooting: weighted average 3PT%
    team_3pt_pct = round(float(players["three_pt_pct"].mean()), 3)

    # True Shooting efficiency: weighted average TS%
    team_ts_pct = round(float(players["ts_pct"].mean()), 3)

    # Turnovers per game: from turnover rate
    topg_projected = round(float(players["turnover_rate"].mean() / 100 * 67 / 5), 1)

    # Offensive and defensive ratings (per 100 possessions)
    team_ortg = round(float(players["offensive_rating"].mean()), 1)
    team_drtg = round(float(players["defensive_rating"].mean()), 1)

    # Net rating = how many more points per 100 possessions vs opponent
    net_rating = round(team_ortg - team_drtg, 1)

    # Win projection: based on net rating
    # In college basketball, roughly every +3.0 net rating = ~2 more wins over a season
    # Average Big Ten team ~20 wins; calibrate from there
    projected_wins = round(max(10.0, min(35.0, 20.0 + net_rating * 0.65)), 1)

    # For Illinois context specifically
    illinois_context_wins = round(max(14.0, min(35.0, projected_wins)), 1)

    # Steals and blocks
    spg = round(float(players["steal_rate"].mean() / 100 * 67), 1)
    bpg = round(float(players["block_rate"].mean() / 100 * 67), 1)

    # ── Internal scoring system metrics (for compatibility) ─────────────────
    offense    = float((team_ortg - 95) * 2)
    defense    = float((115 - team_drtg) * 2.4)
    spacing    = float(team_3pt_pct * 190)
    rebounding = float((players["off_rebound_rate"].mean() + players["def_rebound_rate"].mean()) * 1.9)
    playmaking = float((players["assist_rate"].mean() - players["turnover_rate"].mean()) * 3.2 + 50)
    risk       = float(players["risk_score"].mean() if "risk_score" in players.columns else 45)

    roster_grade = 0.26 * offense + 0.22 * defense + 0.2 * spacing + 0.14 * rebounding + 0.18 * playmaking - 0.12 * risk

    identity = identify_team_identity(offense, defense, spacing, rebounding, playmaking)

    return {
        # Real projected basketball stats (what GMs care about)
        "projected_ppg":        ppg_projected,
        "projected_rpg":        rpg_projected,
        "projected_apg":        apg_projected,
        "projected_orpg":       orpg_projected,
        "projected_drpg":       drpg_projected,
        "projected_spg":        spg,
        "projected_bpg":        bpg,
        "projected_topg":       topg_projected,
        "team_3pt_pct":         team_3pt_pct,
        "team_ts_pct":          team_ts_pct,
        "team_ortg":            team_ortg,
        "team_drtg":            team_drtg,
        "net_rating":           net_rating,
        "projected_wins":       illinois_context_wins,

        # Internal scoring (kept for compatibility)
        "roster_grade":         round(roster_grade, 1),
        "offensive_score":      round(offense, 1),
        "defensive_score":      round(defense, 1),
        "spacing_score":        round(spacing, 1),
        "rebounding_score":     round(rebounding, 1),
        "playmaking_score":     round(playmaking, 1),
        "risk_score":           round(risk, 1),
        "projected_win_impact": illinois_context_wins,   # kept for legacy callers
        "team_identity":        identity.label,
        "team_identity_summary":identity.summary,
    }


def identify_team_identity(offense: float, defense: float, spacing: float, rebounding: float, playmaking: float) -> TeamIdentity:
    if defense > offense + 7 and defense > 45:
        return TeamIdentity("Defensive Juggernaut", "Elite stop-rate profile with rim deterrence and event creation.")
    if spacing > 66 and offense > 44:
        return TeamIdentity("Elite Shooting Team", "Lineup geometry opens driving lanes and forces high-value closeouts.")
    if playmaking > 56 and offense > 45:
        return TeamIdentity("Transition Offense Team", "Ball-movers who can generate early-clock paint touches and kickout threes.")
    if abs(offense - defense) < 5 and min(spacing, rebounding, playmaking) > 42:
        return TeamIdentity("Balanced Contender", "No structural weakness across major possession-winning categories.")
    return TeamIdentity("Hybrid Rotation Team", "Competitive profile with upside tied to role optimization and matchup construction.")


def front_office_insights(players: pd.DataFrame) -> list[dict[str, str]]:
    def pick(df: pd.DataFrame, label: str) -> dict[str, str]:
        row = df.iloc[0]
        return {
            "title": label,
            "player": row["player_name"],
            "summary": (
                f"{row['player_name']} projects as a {row['archetype']} with impact {row['projected_impact_score']:.1f}, "
                f"fit {row['illinois_fit_score']:.1f}, and hidden gem score {row['hidden_gem_score']:.1f}."
            ),
        }

    # Use predicted_bpm if available (from ML ensemble), else fall back to projected_impact_score
    _upside_col = "predicted_bpm" if "predicted_bpm" in players.columns else "projected_impact_score"

    shooter = players.sort_values(["three_pt_pct", "market_inefficiency_score"], ascending=False)
    defender = players.sort_values(["steal_rate", "block_rate", "defensive_rating"], ascending=[False, False, True])
    upside = players.sort_values([_upside_col, "risk_score"], ascending=[False, True])
    wing = players[players["position"].isin(["WI", "PF"])].sort_values(["hidden_gem_score"], ascending=False)
    nba = players.sort_values([_upside_col, "height_inches", "three_pt_pct"], ascending=False)

    return [
        pick(shooter, "Most Undervalued Shooter"),
        pick(defender, "Most Undervalued Defender"),
        pick(upside, "Highest Upside Freshman Transfer"),
        pick(wing if not wing.empty else players, "Best Value Wing"),
        pick(nba, "Most NBA-Like Prospect"),
    ]
