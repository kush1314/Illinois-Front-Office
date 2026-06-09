"""
Training dataset builder.

How we create labeled transfer training data from real public sources:

1. Scrape Basketball Reference advanced stats for seasons 2021 → 2025.
   Each row = one player, one season (school, BPM, TS%, usage, etc.)

2. Match players across consecutive years.
   - Same player_name appearing at School A in year Y and School B in year Y+1
   - If School A ≠ School B → that's a confirmed transfer
   - We build a feature vector from year-Y stats and a BPM label from year Y+1

3. Add conference difficulty adjustment.
   A +3 BPM in the Sun Belt ≠ a +3 BPM in the Big Ten.
   We encode conference strength as a feature so the model learns the translation.

4. Save the dataset to SQLite (historical_transfers table).
   Existing synthetic rows are replaced with real data.

The resulting dataset size depends on scraping success:
  ~4 seasons × ~4,000 players/season → ~2,000–4,000 labeled transfer rows.
  That's enough for Random Forest + XGBoost + MLP to learn real patterns.
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd

from app.data_pipeline.scrapers.basketball_ref import fetch_season

# ── Conference difficulty coefficients ───────────────────────────────────────
# Derived from BartTorvik multi-year average AdjEM differentials.
# Higher = harder conference. Big Ten = reference (1.00).
CONF_DIFFICULTY: dict[str, float] = {
    "Big Ten":   1.00, "Big 12":   0.98, "SEC":      0.96,
    "ACC":       0.94, "Big East": 0.93, "Pac-12":   0.90,
    "A-10":      0.86, "AAC":      0.83, "WCC":      0.82,
    "MVC":       0.79, "MAC":      0.76, "CUSA":     0.74,
    "SBC":       0.72, "Sun Belt": 0.72, "Horizon":  0.71,
    "OVC":       0.69, "NEC":      0.67, "Patriot":  0.67,
    "Ivy":       0.71, "MEAC":     0.63, "SWAC":     0.62,
    "WAC":       0.70, "MAAC":     0.74, "CAA":      0.77,
    "Ind":       0.78,
}

# ── Features that go into the ML model ───────────────────────────────────────
TRAINING_FEATURES = [
    "previous_bpm",
    "previous_bpm_conf_adj",   # BPM × conf difficulty (quality-of-competition adjusted)
    "ts_pct",
    "usage_rate",
    "assist_rate",
    "turnover_rate",
    "off_rebound_rate",
    "def_rebound_rate",
    "steal_rate",
    "block_rate",
    "vorp",
    "games",
    "minutes",
    "conf_strength_from",      # How hard was the origin conference
    "conf_strength_to",        # How hard is the destination conference
    "conf_upgrade",            # Positive = moving to harder conf (tougher prediction)
]


def _get_conf_strength(conf: object) -> float:
    return CONF_DIFFICULTY.get(str(conf).strip(), 0.78)


def build_transfer_dataset(years: list[int] | None = None) -> pd.DataFrame:
    """
    Core pipeline: scrape BBRef, identify real transfers, label outcomes.

    Returns a DataFrame with TRAINING_FEATURES + target columns:
      future_bpm, future_impact_score (0-100 binary × 100 for scale compat)
    """
    if years is None:
        years = [2021, 2022, 2023, 2024, 2025]

    seasons: dict[int, pd.DataFrame] = {}
    for yr in years:
        print(f"[Builder] Scraping Basketball Reference season {yr}…")
        df = fetch_season(yr)
        if not df.empty:
            seasons[yr] = df
            print(f"[Builder]   → {len(df)} players for {yr}")
        else:
            print(f"[Builder]   → FAILED for {yr}, skipping")
        time.sleep(2)  # polite gap between seasons

    if len(seasons) < 2:
        print("[Builder] Fewer than 2 seasons scraped — returning empty.")
        return pd.DataFrame()

    records: list[dict] = []
    sorted_years = sorted(seasons)

    for i in range(len(sorted_years) - 1):
        yr_a, yr_b = sorted_years[i], sorted_years[i + 1]
        df_a = seasons[yr_a]
        df_b = seasons[yr_b]

        # Index year B by (player_name, school) for fast lookup
        b_by_name: dict[str, list[dict]] = {}
        for row in df_b.to_dict("records"):
            name = str(row.get("player_name", "")).strip()
            if name:
                b_by_name.setdefault(name, []).append(row)

        for row_a in df_a.to_dict("records"):
            name = str(row_a.get("player_name", "")).strip()
            if not name:
                continue

            school_a = str(row_a.get("school", "")).strip()
            conf_a   = str(row_a.get("conference", "")).strip()
            bpm_a    = row_a.get("bpm", np.nan)

            if pd.isna(bpm_a):
                continue

            matches_b = b_by_name.get(name, [])
            for row_b in matches_b:
                school_b = str(row_b.get("school", "")).strip()
                conf_b   = str(row_b.get("conference", "")).strip()
                bpm_b    = row_b.get("bpm", np.nan)

                if pd.isna(bpm_b):
                    continue

                transferred = int(school_a != school_b)

                conf_s_a = _get_conf_strength(conf_a)
                conf_s_b = _get_conf_strength(conf_b)
                bpm_a_adj = float(bpm_a) * conf_s_a
                bpm_b_val = float(bpm_b)

                # Success = BPM at destination ≥ 0 (net positive impact)
                success = int(bpm_b_val >= 0.0)
                # Impact score 0-100 (for backwards compat with existing pipeline)
                future_impact = float(np.clip(50 + bpm_b_val * 6, 0, 100))

                records.append({
                    # Identity
                    "player_name":          name,
                    "school":               school_a,
                    "conference":           conf_a,
                    "school_destination":   school_b,
                    "transferred":          transferred,
                    "data_year":            yr_a,
                    # Pre-transfer features
                    "previous_bpm":         float(bpm_a),
                    "previous_bpm_conf_adj": bpm_a_adj,
                    "ts_pct":               float(row_a.get("ts_pct", 0.50)),
                    "usage_rate":           float(row_a.get("usage_rate", 20.0)),
                    "assist_rate":          float(row_a.get("assist_rate", 15.0)),
                    "turnover_rate":        float(row_a.get("turnover_rate", 15.0)),
                    "off_rebound_rate":     float(row_a.get("off_rebound_rate", 5.0)),
                    "def_rebound_rate":     float(row_a.get("def_rebound_rate", 15.0)),
                    "steal_rate":           float(row_a.get("steal_rate", 2.0)),
                    "block_rate":           float(row_a.get("block_rate", 2.0)),
                    "vorp":                 float(row_a.get("vorp", 0.0)),
                    "games":                float(row_a.get("games", 20.0)),
                    "minutes":              float(row_a.get("minutes", 500.0)),
                    "conf_strength_from":   conf_s_a,
                    "conf_strength_to":     conf_s_b,
                    "conf_upgrade":         conf_s_b - conf_s_a,
                    # Per-game stats (for the portal board display)
                    "ppg":  float(row_a.get("ppg", 8.0)),
                    "rpg":  float(row_a.get("rpg", 3.0)),
                    "apg":  float(row_a.get("apg", 1.5)),
                    "three_pt_pct": float(row_a.get("three_pt_pct", 0.33)),
                    "ft_pct":       float(row_a.get("ft_pct", 0.70)),
                    "offensive_rating": float(row_a.get("offensive_rating",
                                               row_a.get("off_win_shares", 0) * 10 + 100)),
                    "defensive_rating": float(row_a.get("defensive_rating", 100.0)),
                    # Targets
                    "future_bpm":           bpm_b_val,
                    "future_impact_score":  future_impact,
                    "transfer_success":     success,
                    # Legacy compat
                    "public_transfer_rank": int(records.__len__() + 1),
                    "weight":               float(row_a.get("weight", 210.0)),
                    "height":               str(row_a.get("height", "6-3")),
                    "position":             str(row_a.get("position", "G")),
                    "class":                str(row_a.get("class_year", "SR")),
                    "ft_pct":               float(row_a.get("ft_pct", 0.70)),
                })

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)
    # Drop NaN-heavy rows
    df = df.dropna(subset=["previous_bpm", "future_bpm", "ts_pct", "usage_rate"])
    # Re-assign public_transfer_rank by model quality (desc future_bpm as proxy)
    df = df.sort_values("future_bpm", ascending=False).reset_index(drop=True)
    df["public_transfer_rank"] = df.index + 1

    transfers = df[df["transferred"] == 1].copy()
    print(f"[Builder] Final: {len(transfers)} transfer rows, {len(df)} total player-year pairs.")
    return df  # return all (model needs non-transfers too as negatives)


def build_portal_board(current_season_df: pd.DataFrame) -> pd.DataFrame:
    """
    Turn a scraped current-season DataFrame into the portal board
    used by all the agents.  Adds the columns the rest of the app expects.
    """
    df = current_season_df.copy()

    # Ensure required columns exist
    defaults = {
        "ppg": 8.0, "rpg": 3.0, "apg": 1.5,
        "three_pt_pct": 0.33, "ft_pct": 0.70,
        "usage_rate": 20.0, "ts_pct": 0.50,
        "assist_rate": 15.0, "turnover_rate": 15.0,
        "off_rebound_rate": 5.0, "def_rebound_rate": 15.0,
        "steal_rate": 2.0, "block_rate": 2.0,
        "offensive_rating": 102.0, "defensive_rating": 100.0,
        "previous_bpm": 0.0, "future_bpm": 0.0,
        "vorp": 0.0, "games": 20.0, "minutes": 500.0,
        "weight": 210.0, "height": "6-3", "position": "G",
        "class": "SR",
    }
    for col, default in defaults.items():
        if col not in df.columns:
            df[col] = default
        else:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(default)

    # Add conference strength feature
    df["conf_strength"] = df["conference"].map(lambda c: _get_conf_strength(c))
    df["conf_strength_from"] = df["conf_strength"]
    df["conf_strength_to"]   = df["conf_strength"]
    df["conf_upgrade"]       = 0.0

    # Public rank by ppg × ts% composite (proxy until ML scores overwrite it)
    df["composite"] = df["ppg"] * df["ts_pct"] * df["games"].clip(upper=35)
    df = df.sort_values("composite", ascending=False).reset_index(drop=True)
    df["public_transfer_rank"] = df.index + 1
    df = df.drop(columns=["composite"])

    # Legacy column: future_impact_score placeholder (will be overwritten by ML)
    df["future_impact_score"] = 50.0

    return df
