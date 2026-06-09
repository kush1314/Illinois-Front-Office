from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

import pandas as pd

from app.config import DATA_DIR, DB_PATH


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db_cursor():
    conn = get_connection()
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
    finally:
        conn.close()


def initialize_database() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    players_path = DATA_DIR / "players.csv"
    historical_path = DATA_DIR / "historical_transfers.csv"
    roster_path = DATA_DIR / "illinois_roster.csv"

    players = pd.read_csv(players_path)
    historical = pd.read_csv(historical_path)
    roster = pd.read_csv(roster_path)

    with get_connection() as conn:
        players.to_sql("players", conn, if_exists="replace", index=False)
        historical.to_sql("historical_transfers", conn, if_exists="replace", index=False)
        roster.to_sql("illinois_roster", conn, if_exists="replace", index=False)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_players_name ON players(player_name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_players_position ON players(position)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_players_rank ON players(public_transfer_rank)")
        conn.commit()


def table_to_df(table: str) -> pd.DataFrame:
    with get_connection() as conn:
        return pd.read_sql_query(f"SELECT * FROM {table}", conn)
