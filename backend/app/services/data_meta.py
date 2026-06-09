"""
Data source metadata for the Illinois Front Office AI platform.
Updated 2026-06-08: player stats are now real 2024-25 BartTorvik data.
"""
from __future__ import annotations

from datetime import date

DATA_META: dict[str, object] = {
    "players": {
        "source": "barttorvik",
        "label": "BartTorvik 2024-25 advanced stats",
        "description": (
            "198 real D1 players from 95 schools — 2024-25 season advanced statistics "
            "sourced from barttorvik.com via getadvstats.php. "
            "Includes Cooper Flagg, Johni Broome, Braden Smith, Ryan Kalkbrenner, "
            "Walter Clayton Jr., and 193 others. "
            "Stats: adBPM, TS%, ORtg, OR%, DR%, A%, TO%, Stl%, 3PT%, FT%, PPG, position. "
            "Note: portal eligibility status is not tracked — these are 2024-25 season profiles, "
            "not a live portal feed."
        ),
        "last_updated": str(date.today()),
        "live_source": "https://barttorvik.com/playerstat.php",
        "scraper": "backend/app/data_pipeline/scrapers/barttorvik.py (Playwright)",
    },
    "historical_transfers": {
        "source": "synthetic",
        "label": "Synthetic ML training data (NCAA-calibrated)",
        "description": (
            "3,000 synthetic transfer outcome profiles calibrated to match real NCAA "
            "statistical distributions. Used to train the RF+XGB+MLP transfer success model. "
            "NOT verified real-world transfer outcome records. Prototype training data."
        ),
        "last_updated": str(date.today()),
        "live_source_possible": "Multi-year Sports Reference longitudinal transfer data",
    },
    "illinois_roster": {
        "source": "barttorvik",
        "label": "Illinois 2024-25 season stats (BartTorvik)",
        "description": (
            "Real Illinois Fighting Illini 2024-25 season data from BartTorvik: "
            "Jakucionis (15.0 PPG), T. Ivisic (13.0 PPG), Will Riley (12.6 PPG), "
            "Kylan Boswell (12.3 PPG), Tre White (10.5 PPG), Ben Humrichous, and others. "
            "As of 2024-25 season. Verify current roster at fightingillini.com."
        ),
        "last_updated": str(date.today()),
        "live_source": "https://barttorvik.com/team.php?team=Illinois",
    },
}


def get_meta(table: str) -> dict[str, object]:
    return DATA_META.get(table, {
        "source": "barttorvik",
        "label": "BartTorvik 2024-25 real stats",
        "last_updated": str(date.today()),
    })
