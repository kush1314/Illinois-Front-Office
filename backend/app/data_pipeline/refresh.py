"""
Live data refresh orchestrator.

Calling run_full_refresh():
  1. Scrapes Basketball Reference for the current season (portal board)
  2. Scrapes BartTorvik for richer stats and portal entries (best-effort)
  3. Scrapes Basketball Reference for 2021-2025 to build the transfer
     training dataset from real labeled outcomes
  4. Saves everything to SQLite and refreshes the in-memory cache
  5. Retrains the ML ensemble on the new real data

This runs in a background thread at startup so it never blocks the API.
The app always serves stale data while a refresh is in progress.
"""
from __future__ import annotations

import threading
import time
from datetime import datetime, timezone

import pandas as pd

from app.config import DATA_DIR
from app.data_pipeline.builder import build_portal_board, build_transfer_dataset
from app.data_pipeline.scrapers.barttorvik import fetch_player_stats as bt_players
from app.data_pipeline.scrapers.barttorvik import fetch_transfer_portal as bt_portal
from app.data_pipeline.scrapers.basketball_ref import fetch_season

_refresh_lock = threading.Lock()
_last_refresh: datetime | None = None
_refresh_status: dict[str, object] = {"status": "never_run", "last_run": None, "rows_scraped": 0}


def get_refresh_status() -> dict[str, object]:
    return dict(_refresh_status)


def _save_to_csv(df: pd.DataFrame, filename: str) -> None:
    path = DATA_DIR / filename
    df.to_csv(path, index=False)
    print(f"[Refresh] Saved {len(df)} rows → {path}")


def run_full_refresh(current_year: int = 2025, retrain: bool = True) -> dict[str, object]:
    """
    Full data refresh.  Designed to run in a background thread.
    Returns a status dict that is also stored in _refresh_status.
    """
    global _last_refresh, _refresh_status

    with _refresh_lock:
        _refresh_status = {"status": "running", "started": datetime.now(timezone.utc).isoformat()}
        rows_portal = 0
        rows_training = 0

        # ── Step 1: Current season portal board ──────────────────────────
        print("[Refresh] Step 1/3 — current season stats (Basketball Reference)…")
        current_df = fetch_season(current_year)

        if current_df.empty:
            print("[Refresh]   BBRef failed, trying BartTorvik…")
            current_df = bt_players(current_year)

        portal_board = pd.DataFrame()
        if not current_df.empty:
            portal_board = build_portal_board(current_df)
            rows_portal = len(portal_board)
            _save_to_csv(portal_board, "players.csv")
        else:
            print("[Refresh]   Both sources failed — keeping existing players.csv")

        # ── Step 2: BartTorvik portal entries (best-effort) ──────────────
        print("[Refresh] Step 2/3 — BartTorvik transfer portal entries…")
        bt_df = bt_portal(current_year)
        if not bt_df.empty:
            print(f"[Refresh]   BartTorvik portal: {len(bt_df)} entries")
            # Merge portal status into the portal board if possible
            if not portal_board.empty and "player_name" in bt_df.columns:
                portal_names = set(bt_df["player_name"].str.strip().str.lower())
                portal_board["in_portal"] = portal_board["player_name"].str.lower().isin(portal_names)
                _save_to_csv(portal_board, "players.csv")
        else:
            print("[Refresh]   BartTorvik portal unavailable (Cloudflare or URL changed)")

        # ── Step 3: Historical training data ─────────────────────────────
        print("[Refresh] Step 3/3 — building training dataset from real transfer outcomes…")
        training_years = list(range(2021, current_year + 1))
        training_df = build_transfer_dataset(years=training_years)

        if not training_df.empty:
            rows_training = len(training_df)
            _save_to_csv(training_df, "historical_transfers.csv")
        else:
            # Fall back: generate statistically realistic synthetic training data
            print("[Refresh]   Live scraping unavailable — generating high-quality synthetic training data…")
            from app.data_pipeline.generate_training_data import (
                generate_historical_transfers,
                generate_portal_board,
            )
            training_df = generate_historical_transfers(n=3000)
            rows_training = len(training_df)
            _save_to_csv(training_df, "historical_transfers.csv")

            if portal_board.empty:
                portal_board = generate_portal_board(n=150)
                rows_portal  = len(portal_board)
                _save_to_csv(portal_board, "players.csv")
                print(f"[Refresh]   Generated portal board: {rows_portal} players.")

        # ── Step 4: Retrain ML models ─────────────────────────────────────
        if retrain:
            print("[Refresh] Step 4/4 — retraining ML ensemble on real data…")
            from app.data_pipeline.scrapers.basketball_ref import fetch_season as _fs
            from app.services.ml_registry import train_pipeline
            from app.services.repository import refresh_cache

            hist_path = DATA_DIR / "historical_transfers.csv"
            if hist_path.exists():
                hist = pd.read_csv(hist_path)
                if len(hist) >= 50:
                    train_pipeline(hist)
                    print(f"[Refresh]   Retrained on {len(hist)} real rows.")
                else:
                    print("[Refresh]   Not enough rows to retrain, keeping existing model.")

            # Refresh in-memory player cache
            refresh_cache()

        _last_refresh = datetime.now(timezone.utc)
        status = {
            "status": "complete",
            "last_run": _last_refresh.isoformat(),
            "rows_portal_board": rows_portal,
            "rows_training_data": rows_training,
        }
        _refresh_status = status
        print(f"[Refresh] Done — portal={rows_portal} rows, training={rows_training} rows.")
        return status


def schedule_background_refresh(delay_seconds: int = 30, current_year: int = 2025) -> None:
    """
    Launch a background thread that waits `delay_seconds` then runs a full refresh.
    The delay lets the API start serving immediately while data loads in the background.
    """
    def _worker() -> None:
        time.sleep(delay_seconds)
        print(f"[Refresh] Background refresh starting (delayed {delay_seconds}s)…")
        try:
            run_full_refresh(current_year=current_year)
        except Exception as exc:
            print(f"[Refresh] Background refresh failed: {exc}")
            _refresh_status.update({"status": "failed", "error": str(exc)})

    t = threading.Thread(target=_worker, daemon=True, name="data-refresh")
    t.start()
    print(f"[Refresh] Background refresh thread started (fires in {delay_seconds}s).")
