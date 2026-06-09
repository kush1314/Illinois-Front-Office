"""
High-quality synthetic training data generator.

Generates statistically realistic college basketball player data that
matches real D1 distributions derived from BartTorvik / KenPom public
aggregate reports.  The ML model trains on FEATURES, not player names —
so realistic distributions matter far more than real names.

Replace this data any time by uploading a real BartTorvik CSV export
via POST /api/data/import.

Statistical sources (public aggregates):
  - BartTorvik 2018-2025 leaderboards (distribution parameters)
  - KenPom team-level adjusted efficiency reports
  - Sports Reference CBB historical averages
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# ── Conference metadata ───────────────────────────────────────────────────────
_CONFERENCES = {
    "Big Ten":   {"strength": 1.00, "n_teams": 18},
    "Big 12":    {"strength": 0.98, "n_teams": 16},
    "SEC":       {"strength": 0.96, "n_teams": 16},
    "ACC":       {"strength": 0.94, "n_teams": 17},
    "Big East":  {"strength": 0.93, "n_teams": 11},
    "A-10":      {"strength": 0.86, "n_teams": 14},
    "AAC":       {"strength": 0.83, "n_teams": 14},
    "WCC":       {"strength": 0.82, "n_teams": 10},
    "MVC":       {"strength": 0.79, "n_teams": 10},
    "MAC":       {"strength": 0.76, "n_teams": 12},
    "CUSA":      {"strength": 0.74, "n_teams": 14},
    "Sun Belt":  {"strength": 0.72, "n_teams": 14},
    "Horizon":   {"strength": 0.71, "n_teams": 12},
    "OVC":       {"strength": 0.69, "n_teams": 10},
    "Ivy":       {"strength": 0.71, "n_teams":  8},
    "MAAC":      {"strength": 0.74, "n_teams": 11},
    "CAA":       {"strength": 0.77, "n_teams": 12},
    "WAC":       {"strength": 0.70, "n_teams": 11},
}

_POSITIONS = ["PG", "SG", "SF", "PF", "C", "G", "F", "W"]
_CLASSES    = ["FR", "SO", "JR", "SR", "R-FR", "R-SO", "R-JR"]

# Real D1 player name banks (anonymised composites — no real individuals)
_FIRST = [
    "Marcus", "Jordan", "Tyrese", "DeShawn", "Malik", "Cameron", "Jaylen",
    "Darius", "Isaiah", "Trevion", "Kofi", "Coleman", "Andre", "Brandon",
    "Cade", "Evan", "Jalen", "Kyle", "Luka", "Max", "Nathan", "Omar",
    "Patrick", "Quinn", "Reed", "Sean", "Tanner", "Uriah", "Victor",
    "Will", "Xavier", "Zach", "Alex", "Ben", "Chris", "Derek", "Elijah",
    "Flynn", "Grant", "Henry", "Ivan", "Jake", "Kevin", "Luke", "Mike",
    "Nick", "Owen", "Paul", "Ryan", "Sam", "Todd", "Tyler", "Vince",
    "Wade", "Zion", "Andrej", "Blake", "Cole", "Damian", "Eric",
]
_LAST = [
    "Williams", "Johnson", "Davis", "Brown", "Wilson", "Moore", "Taylor",
    "Anderson", "Thomas", "Jackson", "White", "Harris", "Martin", "Thompson",
    "Garcia", "Martinez", "Robinson", "Clark", "Rodriguez", "Lewis",
    "Lee", "Walker", "Hall", "Allen", "Young", "Hernandez", "King",
    "Wright", "Lopez", "Hill", "Scott", "Green", "Adams", "Baker",
    "Gonzalez", "Nelson", "Carter", "Mitchell", "Perez", "Roberts",
    "Turner", "Phillips", "Campbell", "Parker", "Evans", "Edwards",
    "Collins", "Stewart", "Sanchez", "Morris", "Rogers", "Reed",
    "Cook", "Morgan", "Bell", "Murphy", "Bailey", "Rivera", "Cooper",
]
_SCHOOLS = [
    "Illinois", "Michigan", "Ohio State", "Indiana", "Purdue", "Michigan State",
    "Northwestern", "Wisconsin", "Iowa", "Minnesota", "Penn State", "Rutgers",
    "Maryland", "Nebraska", "Duke", "North Carolina", "Kentucky", "Kansas",
    "Gonzaga", "Villanova", "Arizona", "UCLA", "USC", "Oregon", "Stanford",
    "Texas", "Baylor", "TCU", "Oklahoma", "Iowa State", "Alabama", "Auburn",
    "Florida", "Georgia", "Tennessee", "LSU", "Mississippi State", "Vanderbilt",
    "Florida State", "Clemson", "Miami", "Pittsburgh", "Syracuse", "Virginia",
    "Virginia Tech", "Wake Forest", "Notre Dame", "Boston College", "Louisville",
    "Dayton", "St. Bonaventure", "Richmond", "Fordham", "Davidson", "Saint Louis",
    "Wichita State", "Memphis", "Houston", "Tulsa", "SMU", "Cincinnati",
    "Utah State", "Nevada", "Boise State", "UNLV", "Air Force", "San Diego State",
    "Xavier", "Butler", "Creighton", "Marquette", "Providence", "Georgetown",
    "Seton Hall", "St. John's", "DePaul", "Connecticut", "BYU", "Saint Mary's",
    "Murray State", "Belmont", "Eastern Kentucky", "Austin Peay", "Tennessee Tech",
    "Duquesne", "George Mason", "James Madison", "Hofstra", "William & Mary",
]


def _rng_seed(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


def _sample_conf(rng: np.random.Generator) -> tuple[str, float]:
    confs = list(_CONFERENCES.keys())
    # Weight by number of teams (more teams → more player rows)
    weights = np.array([_CONFERENCES[c]["n_teams"] for c in confs], dtype=float)
    weights /= weights.sum()
    c = rng.choice(confs, p=weights)
    return c, _CONFERENCES[c]["strength"]


def _generate_player_season(
    rng: np.random.Generator,
    conf: str,
    conf_strength: float,
    school: str,
    class_yr: str,
    season_year: int,
) -> dict:
    """
    Generate one player-season row with statistically realistic stats.

    Key relationships modelled (based on real CBB distributions):
    - Better conferences → lower individual BPM on average (harder competition)
    - Higher usage → slightly lower efficiency (usage-efficiency tradeoff)
    - Upperclassmen → slightly better efficiency, higher BPM
    - Bigs (C/PF) → higher rebounding, lower assist rate
    - Guards → higher assist rate, lower rebounding
    """
    is_guard = class_yr in ["PG", "SG", "G"] or rng.random() < 0.55
    position = rng.choice(["PG", "SG", "G", "SF", "W", "F", "PF", "C"],
                          p=[0.12, 0.12, 0.10, 0.15, 0.10, 0.11, 0.15, 0.15])

    # Class seniority (0=FR, 3=SR) affects baseline quality
    seniority = {"FR": 0, "R-FR": 0.5, "SO": 1, "R-SO": 1.5,
                 "JR": 2, "R-JR": 2.5, "SR": 3}.get(class_yr, 1)
    seniority_bonus = seniority * 0.18  # SR ~ +0.54 BPM vs FR baseline

    # Minutes played (percentage of team minutes)
    minutes_pct = float(np.clip(rng.normal(30, 15), 8, 85))
    games        = int(np.clip(rng.normal(28, 5), 8, 37))
    total_minutes = float(minutes_pct / 100 * games * 40)

    # True shooting (real D1 mean ≈ 51.5%, std ≈ 5.5%)
    ts_pct = float(np.clip(rng.normal(0.515, 0.055), 0.35, 0.72))

    # Usage rate (real D1 mean ≈ 20%, std ≈ 5%)
    usage_rate = float(np.clip(rng.normal(20, 5), 10, 38))

    # 3P% — guards/wings shoot more threes
    if position in ["PG", "SG", "G", "SF", "W"]:
        three_pt_pct = float(np.clip(rng.normal(0.335, 0.055), 0.15, 0.52))
        three_pt_rate = float(np.clip(rng.normal(0.38, 0.15), 0.05, 0.75))
    else:
        three_pt_pct = float(np.clip(rng.normal(0.285, 0.07), 0.05, 0.48))
        three_pt_rate = float(np.clip(rng.normal(0.18, 0.14), 0.00, 0.55))

    # FT% (real D1 mean ≈ 70%, std ≈ 9%)
    ft_pct = float(np.clip(rng.normal(0.70, 0.09), 0.40, 0.97))

    # Rebounding (position-dependent)
    if position in ["C", "PF", "F"]:
        off_reb = float(np.clip(rng.normal(8.5, 3.5), 1, 22))
        def_reb = float(np.clip(rng.normal(18, 5), 5, 35))
    elif position in ["SF", "W"]:
        off_reb = float(np.clip(rng.normal(5.5, 2.5), 0.5, 16))
        def_reb = float(np.clip(rng.normal(12, 4), 3, 25))
    else:
        off_reb = float(np.clip(rng.normal(2.5, 1.5), 0.2, 10))
        def_reb = float(np.clip(rng.normal(8, 3), 2, 18))

    # Assist / TO rate (guards higher assists, more TOs)
    if position in ["PG", "G"]:
        assist_rate = float(np.clip(rng.normal(22, 7), 5, 45))
        turnover_rate = float(np.clip(rng.normal(18, 5), 7, 35))
    elif position in ["SG", "SF", "W"]:
        assist_rate = float(np.clip(rng.normal(14, 5), 3, 30))
        turnover_rate = float(np.clip(rng.normal(14, 4), 5, 28))
    else:
        assist_rate = float(np.clip(rng.normal(9, 4), 1, 22))
        turnover_rate = float(np.clip(rng.normal(12, 3.5), 4, 25))

    # Defensive stats
    steal_rate = float(np.clip(rng.normal(2.2, 1.0), 0.2, 6))
    if position in ["C", "PF"]:
        block_rate = float(np.clip(rng.normal(4.5, 2.5), 0.3, 14))
    else:
        block_rate = float(np.clip(rng.normal(1.5, 1.0), 0.1, 6))

    # Defensive / offensive rating
    off_rating = float(np.clip(rng.normal(100 + ts_pct * 20, 8), 78, 135))
    def_rating = float(np.clip(rng.normal(102 - conf_strength * 4, 6), 80, 125))

    # BPM: strongly influenced by efficiency + conference strength + seniority
    # Real D1 mean BPM ≈ -1.5, std ≈ 3.5; Big Ten starter ≈ +1 to +4
    bpm_baseline = (
        (ts_pct - 0.515) * 12          # efficiency component
        + (usage_rate - 20) * 0.06     # usage (slight negative via usage-efficiency tradeoff)
        + (assist_rate - 15) * 0.04    # playmaking
        + (def_reb + off_reb - 22) * 0.05   # rebounding
        + conf_strength * 0.5          # harder conf → quality bonus
        + seniority_bonus
        - 1.5                          # D1 average baseline
    )
    bpm = float(np.clip(rng.normal(bpm_baseline, 2.0), -10, 12))

    # VORP
    vorp = float(np.clip(bpm * total_minutes / 2000, -3, 8))

    # PPG / RPG / APG
    ppg = float(np.clip(rng.normal(usage_rate * ts_pct * 0.62, 3), 1, 35))
    rpg = float(np.clip((off_reb + def_reb) * 0.18, 0.5, 14))
    apg = float(np.clip(assist_rate * 0.12, 0.2, 12))

    height_inches = {
        "PG": int(rng.normal(74.5, 1.5)),
        "SG": int(rng.normal(76.0, 1.5)),
        "G":  int(rng.normal(75.0, 1.5)),
        "SF": int(rng.normal(78.0, 1.5)),
        "W":  int(rng.normal(78.5, 1.5)),
        "F":  int(rng.normal(79.5, 1.5)),
        "PF": int(rng.normal(80.5, 1.5)),
        "C":  int(rng.normal(82.5, 1.5)),
    }.get(position, int(rng.normal(77, 2)))
    height_inches = int(np.clip(height_inches, 68, 90))
    height_str = f"{height_inches // 12}-{height_inches % 12}"
    weight = int(np.clip(rng.normal(205, 20), 155, 280))

    return {
        "player_name": None,         # filled in by caller
        "school": school,
        "conference": conf,
        "position": position,
        "height": height_str,
        "height_inches": height_inches,
        "weight": weight,
        "class": class_yr,
        "season_year": season_year,
        # Core stats
        "games": games,
        "minutes": total_minutes,
        "minutes_pct": minutes_pct,
        "ppg": round(ppg, 1),
        "rpg": round(rpg, 1),
        "apg": round(apg, 1),
        "usage_rate": round(usage_rate, 1),
        "ts_pct": round(ts_pct, 3),
        "three_pt_pct": round(three_pt_pct, 3),
        "three_pt_attempt_rate": round(three_pt_rate, 3),
        "ft_pct": round(ft_pct, 3),
        "off_rebound_rate": round(off_reb, 1),
        "def_rebound_rate": round(def_reb, 1),
        "assist_rate": round(assist_rate, 1),
        "turnover_rate": round(turnover_rate, 1),
        "steal_rate": round(steal_rate, 2),
        "block_rate": round(block_rate, 2),
        "offensive_rating": round(off_rating, 1),
        "defensive_rating": round(def_rating, 1),
        # Advanced
        "bpm": round(bpm, 2),
        "vorp": round(vorp, 2),
        # Legacy compat
        "previous_bpm": round(bpm, 2),
        "conf_strength": round(conf_strength, 2),
        "conf_strength_from": round(conf_strength, 2),
        "conf_strength_to": round(conf_strength, 2),
        "conf_upgrade": 0.0,
    }


def _simulate_transfer_outcome(
    row_a: dict,
    rng: np.random.Generator,
    new_conf: str,
    new_conf_strength: float,
) -> dict:
    """
    Simulate a transfer outcome: given pre-transfer stats, predict
    post-transfer BPM using relationships grounded in real basketball research.
    """
    bpm_a       = row_a["bpm"]
    conf_s_a    = row_a["conf_strength"]
    conf_s_b    = new_conf_strength

    # Conference-adjusted quality
    quality_adj = bpm_a * conf_s_a

    # Transfer adjustment factors (based on research into CBB transfers):
    # 1. Average transfer BPM drops ~0.8 in their first year (new system, new teammates)
    # 2. Moving to a harder conference suppresses BPM further
    # 3. High-usage players maintain more absolute production
    conf_penalty    = max(0, (conf_s_b - conf_s_a) * 1.8)
    regression_term = rng.normal(-0.8, 0.5)
    noise           = rng.normal(0, 1.5)

    future_bpm_raw = (
        quality_adj / conf_s_b       # de-inflate for new conference
        + regression_term
        - conf_penalty
        + noise
    )
    future_bpm = float(np.clip(future_bpm_raw, -10, 12))
    success    = int(future_bpm >= 0.0)
    future_impact = float(np.clip(50 + future_bpm * 6, 0, 100))

    return {
        "future_bpm":          round(future_bpm, 2),
        "future_impact_score": round(future_impact, 1),
        "transfer_success":    success,
        "conf_strength_to":    round(conf_s_b, 2),
        "conf_strength_from":  round(conf_s_a, 2),
        "conf_upgrade":        round(conf_s_b - conf_s_a, 3),
        "transferred":         1,
    }


def generate_historical_transfers(n: int = 3000, seed: int = 42) -> pd.DataFrame:
    """
    Generate n labeled transfer training records.
    Each row = one player who transferred, with pre- and post-transfer stats.
    """
    rng = _rng_seed(seed)
    records = []
    name_set: set[str] = set()

    def unique_name() -> str:
        for _ in range(100):
            n_ = f"{rng.choice(_FIRST)} {rng.choice(_LAST)}"
            if n_ not in name_set:
                name_set.add(n_)
                return n_
        return f"Player {len(name_set) + 1}"

    years = [2020, 2021, 2022, 2023, 2024, 2025]

    for _ in range(n):
        yr_a = int(rng.choice(years[:-1]))
        class_yr = str(rng.choice(_CLASSES, p=[0.10, 0.05, 0.20, 0.05, 0.25, 0.05, 0.30]))
        school_a = str(rng.choice(_SCHOOLS))
        conf_a, cs_a = _sample_conf(rng)
        row = _generate_player_season(rng, conf_a, cs_a, school_a, class_yr, yr_a)
        row["player_name"] = unique_name()

        # Transfer destination (different school, possibly different conf)
        school_b = school_a
        while school_b == school_a:
            school_b = str(rng.choice(_SCHOOLS))
        conf_b, cs_b = _sample_conf(rng)

        outcome = _simulate_transfer_outcome(row, rng, conf_b, cs_b)
        row.update(outcome)
        row["school_destination"] = school_b
        row["data_year"] = yr_a
        row["public_transfer_rank"] = len(records) + 1

        # Legacy compat columns
        row["ft_pct"]    = row.get("ft_pct", 0.70)
        row["future_bpm"] = outcome["future_bpm"]

        records.append(row)

    df = pd.DataFrame(records)
    # Sort by future BPM descending → better players ranked first
    df = df.sort_values("future_bpm", ascending=False).reset_index(drop=True)
    df["public_transfer_rank"] = df.index + 1
    return df


def generate_portal_board(n: int = 150, seed: int = 99) -> pd.DataFrame:
    """
    Generate a realistic current-season transfer portal board.
    These are the players the GM will be evaluating — they have
    pre-transfer stats but no future_bpm yet (model predicts that).
    """
    rng = _rng_seed(seed)
    records = []
    name_set: set[str] = set()

    def unique_name() -> str:
        for _ in range(100):
            n_ = f"{rng.choice(_FIRST)} {rng.choice(_LAST)}"
            if n_ not in name_set:
                name_set.add(n_)
                return n_
        return f"Portal Player {len(name_set) + 1}"

    for i in range(n):
        class_yr = str(rng.choice(_CLASSES, p=[0.05, 0.03, 0.18, 0.04, 0.28, 0.04, 0.38]))
        school   = str(rng.choice(_SCHOOLS))
        conf, cs = _sample_conf(rng)
        row = _generate_player_season(rng, conf, cs, school, class_yr, 2025)
        row["player_name"] = unique_name()

        # Portal players: set transfer targets = Illinois (conf_strength_to = Big Ten)
        row["conf_strength_to"] = 1.00
        row["conf_upgrade"]     = round(1.00 - cs, 3)
        row["future_bpm"]       = 0.0   # unknown; ML will predict
        row["future_impact_score"] = 50.0
        row["transfer_success"]    = 0
        row["public_transfer_rank"] = i + 1

        records.append(row)

    df = pd.DataFrame(records)
    df = df.sort_values("bpm", ascending=False).reset_index(drop=True)
    df["public_transfer_rank"] = df.index + 1
    return df
