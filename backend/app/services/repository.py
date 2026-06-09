from __future__ import annotations

from functools import lru_cache

import pandas as pd

from app.db import table_to_df
from app.services.analytics import add_archetypes, add_core_scores


@lru_cache(maxsize=1)
def get_players_enriched() -> pd.DataFrame:
    players = table_to_df("players")
    enriched = add_core_scores(players)
    enriched = add_archetypes(enriched)
    return enriched


@lru_cache(maxsize=1)
def get_historical() -> pd.DataFrame:
    return table_to_df("historical_transfers")


@lru_cache(maxsize=1)
def get_illinois_roster() -> pd.DataFrame:
    return table_to_df("illinois_roster")


def refresh_cache() -> None:
    get_players_enriched.cache_clear()
    get_historical.cache_clear()
    get_illinois_roster.cache_clear()
