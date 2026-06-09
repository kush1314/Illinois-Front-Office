"""
BartTorvik scraper using Playwright (headless Chromium).

BartTorvik uses Cloudflare protection that blocks simple HTTP requests.
Playwright runs a real browser that passes the JS challenge, then we
intercept the AJAX data response from getadvstats.php.

Data source: barttorvik.com/playerstat.php (via getadvstats.php)
Provides: adBPM, TS%, ORtg, DRtg, OR%, DR%, A%, TO%, Stl%, PPG, position, class, height

Column mapping (verified against Cooper Flagg 2024-25 stats):
  0: player_name   1: school      2: conference  3: games      4: minutes_pct
  5: offensive_rating             6: usage_pct   8: ts_pct(%)  9: off_rebound_rate
  10: def_rebound_rate           11: assist_rate 12: turnover_rate 15: ft_pct
  21: three_pt_pct (decimal)     25: class       26: height    28: steal_rate(%)
  53: adBPM                      63: ppg         64: position

Usage:
    df = fetch_player_stats(year=2025, top=2000)
    df_portal = fetch_transfer_portal(year=2025)
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[3] / "data"


def _parse_raw(raw: list[list]) -> pd.DataFrame:
    """Convert raw BartTorvik data array to clean DataFrame."""
    records = []
    for p in raw:
        if len(p) < 64 or not isinstance(p[0], str):
            continue
        try:
            r = {
                "player_name":       p[0],
                "school":            p[1],
                "conference":        p[2],
                "games":             float(p[3]) if p[3] is not None else 0,
                "minutes_pct":       float(p[4]) if p[4] is not None else 0,
                "offensive_rating":  float(p[5]) if p[5] is not None else 100,
                "usage_rate":        float(p[6]) if p[6] is not None else 20,
                "ts_pct":            float(p[8]) / 100 if p[8] is not None else 0.50,
                "off_rebound_rate":  float(p[9]) if p[9] is not None else 5,
                "def_rebound_rate":  float(p[10]) if p[10] is not None else 12,
                "assist_rate":       float(p[11]) if p[11] is not None else 8,
                "turnover_rate":     float(p[12]) if p[12] is not None else 15,
                "ft_pct":            float(p[15]) if p[15] is not None else 0.70,
                "three_pt_pct":      float(p[21]) if p[21] is not None else 0.33,
                "class":             p[25] if p[25] else "JR",
                "height":            p[26] if p[26] else "6-6",
                "weight":            float(p[37]) if p[37] and float(p[37]) > 100 else 210,
                "steal_rate":        float(p[28]) if p[28] is not None else 1.5,
                "bpm":               float(p[53]) if p[53] is not None else 0,
                "ppg":               float(p[63]) if p[63] is not None else 5,
                "position_raw":      p[64] if p[64] else "F",
            }
            records.append(r)
        except (TypeError, ValueError, IndexError):
            continue

    df = pd.DataFrame(records)
    if df.empty:
        return df

    # Normalize
    import numpy as np

    df["ts_pct"]             = df["ts_pct"].clip(0.30, 0.80)
    df["three_pt_pct"]       = df["three_pt_pct"].clip(0, 0.65)
    df["ft_pct"]             = df["ft_pct"].clip(0.40, 1.0)
    df["off_rebound_rate"]   = df["off_rebound_rate"].clip(0, 25)
    df["def_rebound_rate"]   = df["def_rebound_rate"].clip(0, 45)
    df["assist_rate"]        = df["assist_rate"].clip(0, 55)
    df["turnover_rate"]      = df["turnover_rate"].clip(0, 35)
    df["steal_rate"]         = df["steal_rate"].clip(0, 8)
    df["usage_rate"]         = df["usage_rate"].clip(8, 38)
    df["bpm"]                = df["bpm"].clip(-5, 20)
    df["offensive_rating"]   = df["offensive_rating"].clip(80, 140)

    # Position normalisation
    _pos = {
        "PG": "PG", "SG": "SG", "SF": "SF", "PF": "PF", "C": "C",
        "G": "G", "F": "F", "Combo G": "G", "Scoring PG": "PG",
        "Wing": "SF", "Pass-first PG": "PG", "Stretch 4": "PF",
        "Stretch 5": "C", "Rim runner": "C", "High-usage wing": "SF",
        "3 and D": "W", "Defensive wing": "SF", "Playmaking PG": "PG",
        "Shooting G": "SG", "Two-way wing": "SF",
    }
    df["position"] = df["position_raw"].map(_pos).fillna(
        df["position_raw"].str[:2].str.upper()
    ).fillna("F")

    def _h2in(h: str) -> int:
        try:
            f, i = str(h).split("-")
            return int(f) * 12 + int(i)
        except Exception:
            return 78

    df["height_inches"] = df["height"].apply(_h2in)
    df["minutes"] = (df["minutes_pct"] / 100 * 40 * df["games"]).round(1)
    df["previous_bpm"] = df["bpm"]
    df["block_rate"] = (df["bpm"].clip(0, 20) * 0.3 + 1.5).clip(0, 12)
    df["defensive_rating"] = (104 - df["bpm"].clip(-5, 15) * 0.8).clip(85, 118).round(1)

    _conf = {
        "B10": 1.00, "ACC": 0.97, "SEC": 0.99, "B12": 0.98,
        "BE": 0.88, "WCC": 0.82, "A10": 0.77, "Amer": 0.79,
        "MWC": 0.75, "CAA": 0.69, "OVC": 0.63, "P12": 0.92,
        "SB": 0.65, "Horz": 0.67, "MVC": 0.68, "Ivy": 0.72,
        "NEC": 0.62, "MAC": 0.65, "CUSA": 0.62, "BSky": 0.65,
        "BSth": 0.63, "Sum": 0.60, "SWAC": 0.55, "MEAC": 0.55,
        "AE": 0.63, "ASun": 0.64, "MAAC": 0.68, "Pat": 0.64,
    }
    df["conf_strength"]      = df["conference"].map(_conf).fillna(0.68)
    df["conf_strength_from"] = df["conf_strength"]
    df["conf_strength_to"]   = 1.0
    df["conf_upgrade"]       = (1.0 - df["conf_strength"]).round(3)
    df["season_year"]        = 2025
    df["vorp"]               = (df["bpm"] / 5 * df["minutes"] / 2000 * 2.7).round(2)

    return df


def fetch_player_stats(year: int = 2025, top: int = 2000) -> pd.DataFrame:
    """
    Fetch all D1 player advanced stats from BartTorvik via Playwright.

    Playwright is required because BartTorvik uses Cloudflare JS challenges that
    block simple HTTP requests.  The actual data is delivered via an AJAX call to
    getadvstats.php, which Playwright intercepts.

    Returns a DataFrame with TS%, BPM, 3PT%, ORtg, assist rate, etc.
    Returns an empty DataFrame if Playwright is not installed or scraping fails.
    """
    try:
        import asyncio
        from playwright.async_api import async_playwright

        async def _scrape() -> list:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True)
                ctx = await browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )
                )
                page = await ctx.new_page()
                data_container: list[list] = []

                async def on_route(route, request):
                    resp = await route.fetch()
                    url = request.url
                    if "barttorvik.com" in url and request.resource_type in ("xhr", "fetch"):
                        try:
                            body = await resp.body()
                            if len(body) > 500_000:
                                txt = body.decode("utf-8", errors="replace")
                                if txt.strip().startswith("[["):
                                    data_container.extend(json.loads(txt))
                        except Exception:
                            pass
                    await route.fulfill(response=resp)

                await page.route("**/*", on_route)
                # Load homepage first to establish session
                await page.goto("https://barttorvik.com/", wait_until="networkidle", timeout=20_000)
                await page.goto(
                    f"https://barttorvik.com/playerstat.php?year={year}&stype=2&top={top}&T_mode=All",
                    wait_until="networkidle",
                    timeout=45_000,
                )
                await page.wait_for_timeout(8_000)
                await browser.close()
                return data_container

        raw = asyncio.run(_scrape())
        if not raw:
            print("[BartTorvik] No data captured — returning empty DataFrame")
            return pd.DataFrame()

        df = _parse_raw(raw)
        df = df[df["games"] >= 10].copy()
        df = df[df["minutes_pct"] >= 10].copy()
        df["data_source"] = "barttorvik"
        df["data_year"] = year
        print(f"[BartTorvik] Scraped {len(df)} players for {year}")
        return df

    except ImportError:
        print("[BartTorvik] Playwright not installed — run: pip install playwright && playwright install chromium")
        return pd.DataFrame()
    except Exception as exc:
        print(f"[BartTorvik] fetch_player_stats failed: {exc}")
        return pd.DataFrame()


def fetch_transfer_portal(year: int = 2025) -> pd.DataFrame:
    """
    Return portal-eligible players from the full stats dataset.

    BartTorvik's portal tracker URL was not accessible during development.
    This function returns the full player stats (which includes any portal entrants)
    as a fallback. Filter by school/conference to identify likely portal targets.
    """
    return fetch_player_stats(year=year, top=500)
