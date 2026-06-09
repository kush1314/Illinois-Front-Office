"""
Basketball Reference scraper.

Fetches real college basketball advanced stats and per-game stats.
BPM (Box Plus/Minus) from here is the ground-truth outcome variable
we train the ML models to predict.

Rate-limited to respect sports-reference.com's crawl policy.
"""
from __future__ import annotations

import time
from io import StringIO

import pandas as pd
import requests

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept": "text/html,application/xhtml+xml",
    "Connection": "keep-alive",
}

_ADVANCED_RENAME = {
    "Player": "player_name",
    "School": "school",
    "Conf": "conference",
    "G": "games",
    "MP": "minutes",
    "TS%": "ts_pct",
    "3PAr": "three_pt_attempt_rate",
    "FTr": "ft_rate",
    "ORB%": "off_rebound_rate",
    "DRB%": "def_rebound_rate",
    "TRB%": "total_rebound_rate",
    "AST%": "assist_rate",
    "STL%": "steal_rate",
    "BLK%": "block_rate",
    "TOV%": "turnover_rate",
    "USG%": "usage_rate",
    "OWS": "off_win_shares",
    "DWS": "def_win_shares",
    "WS": "win_shares",
    "OBPM": "offensive_bpm",
    "DBPM": "defensive_bpm",
    "BPM": "bpm",
    "VORP": "vorp",
}

_PERGAME_RENAME = {
    "Player": "player_name",
    "School": "school",
    "Conf": "conference",
    "G": "games_pg",
    "MP": "mpg",
    "FG%": "fg_pct",
    "3P": "threes_made",
    "3PA": "threes_att",
    "3P%": "three_pt_pct",
    "FT%": "ft_pct",
    "ORB": "orpg",
    "DRB": "drpg",
    "TRB": "rpg",
    "AST": "apg",
    "STL": "spg",
    "BLK": "bpg",
    "TOV": "topg",
    "PTS": "ppg",
}

# Position lookup from a player's individual page — we infer position from
# context or fall back to this mapping based on school/archetype later.
_POSITION_MAP = {
    "G": "G", "F": "F", "C": "C",
    "PG": "PG", "SG": "SG", "SF": "SF", "PF": "PF",
    "G-F": "G", "F-G": "F", "F-C": "F", "C-F": "C",
}


def _clean_df(df: pd.DataFrame, rename_map: dict[str, str]) -> pd.DataFrame:
    """Rename, drop blank/repeat header rows, coerce numerics."""
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    # Drop rows where player_name is NaN or looks like a repeated header
    if "player_name" in df.columns:
        df = df[df["player_name"].notna()]
        df = df[df["player_name"] != "Player"]
        df = df[~df["player_name"].str.startswith("Rk", na=True)]
    # Coerce all remaining columns to numeric where possible
    for col in df.columns:
        if col not in ("player_name", "school", "conference", "class_year", "position"):
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.reset_index(drop=True)


def fetch_advanced_stats(year: int, delay: float = 3.5) -> pd.DataFrame:
    """
    Fetch all D1 player advanced stats for a season from Basketball Reference.

    'year' is the year the season ENDS (e.g. 2025 = 2024-25 season).
    Returns a DataFrame with BPM, TS%, USG%, rebounding, etc.
    Rate-limited by 'delay' seconds to respect the site.
    """
    url = f"https://www.sports-reference.com/cbb/seasons/men/{year}-advanced.html"
    time.sleep(delay)
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=25)
        resp.raise_for_status()
        tables = pd.read_html(StringIO(resp.text))
        if not tables:
            return pd.DataFrame()
        # The stats table is usually the largest one
        df = max(tables, key=len)
        df = _clean_df(df, _ADVANCED_RENAME)
        df["data_year"] = year
        df["data_source"] = "basketball_reference_advanced"
        # Only keep players with meaningful sample
        if "games" in df.columns:
            df = df[df["games"].fillna(0) >= 8]
        return df
    except Exception as exc:
        print(f"[BBRef-Advanced] year={year} failed: {exc}")
        return pd.DataFrame()


def fetch_pergame_stats(year: int, delay: float = 3.5) -> pd.DataFrame:
    """
    Fetch per-game stats (PPG, RPG, APG, 3P%, FT%, etc.) from Basketball Reference.
    Merged with advanced stats to build a complete player profile.
    """
    url = f"https://www.sports-reference.com/cbb/seasons/men/{year}-per_g.html"
    time.sleep(delay)
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=25)
        resp.raise_for_status()
        tables = pd.read_html(StringIO(resp.text))
        if not tables:
            return pd.DataFrame()
        df = max(tables, key=len)
        df = _clean_df(df, _PERGAME_RENAME)
        df["data_year"] = year
        return df
    except Exception as exc:
        print(f"[BBRef-PerGame] year={year} failed: {exc}")
        return pd.DataFrame()


def fetch_season(year: int) -> pd.DataFrame:
    """
    Fetch and merge advanced + per-game stats for one season.
    Returns a unified player DataFrame suitable for the ML pipeline.
    """
    adv = fetch_advanced_stats(year, delay=3.5)
    if adv.empty:
        return pd.DataFrame()
    pg = fetch_pergame_stats(year, delay=3.5)
    if pg.empty:
        # Return advanced only — per-game is supplemental
        return adv

    merge_keys = ["player_name", "school", "conference"]
    # Keep only the columns we want from per-game to avoid collisions
    pg_cols = merge_keys + [c for c in _PERGAME_RENAME.values() if c not in merge_keys and c in pg.columns]
    pg_sub = pg[[c for c in pg_cols if c in pg.columns]].copy()

    merged = adv.merge(pg_sub, on=merge_keys, how="left")
    return merged
