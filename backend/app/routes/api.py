from __future__ import annotations

from io import StringIO

import pandas as pd
from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import Response

from app.schemas import ChatRequest, ChatResponse, CompareRequest, PredictionResponse, RecruitingQuery, RosterRequest, ScoutingReportResponse
from app.services.analytics import compute_similarity, front_office_insights, rank_targets, roster_outcomes
from app.services.chat_service import chat_response
from app.services.data_meta import DATA_META, get_meta
from app.services.ml_registry import get_pipeline, train_pipeline
from app.services.pdf_service import build_scouting_pdf
from app.services.repository import get_historical, get_illinois_roster, get_players_enriched


router = APIRouter(prefix="/api", tags=["Illinois Front Office AI"])


def ensure_models_trained() -> None:
    pipeline = get_pipeline()
    try:
        pipeline.get_model_performance()
    except RuntimeError:
        train_pipeline(get_historical())


# Kept for backward compat — callers in main.py import this name
ml_pipeline = get_pipeline()


@router.get("/health")
def health() -> dict[str, str]:
    pipeline = get_pipeline()
    trained = pipeline.is_trained()
    perf: dict[str, object] = {}
    if trained:
        try:
            perf = pipeline.get_model_performance()
        except Exception:
            pass
    return {
        "status": "ok",
        "service": "Illinois Front Office AI",
        "ml_trained": str(trained),
        "training_rows": str(perf.get("training_rows", "unknown")),
        "model_stack": str(perf.get("model_stack", [])),
    }


@router.get("/data/status")
def data_status() -> dict[str, object]:
    """Return the current state of the live data pipeline."""
    from app.data_pipeline.refresh import get_refresh_status
    status = get_refresh_status()
    pipeline = get_pipeline()
    if pipeline.is_trained():
        status["ml_performance"] = pipeline.get_model_performance()
    return status


@router.post("/data/refresh")
def trigger_refresh(background: bool = True) -> dict[str, object]:
    """
    Trigger a full live data refresh from Basketball Reference and BartTorvik.
    background=true (default): fires in a background thread, returns immediately.
    background=false: blocks until complete (slow — only for debugging).
    """
    from app.data_pipeline.refresh import run_full_refresh, schedule_background_refresh
    if background:
        schedule_background_refresh(delay_seconds=1, current_year=2025)
        return {"status": "refresh_scheduled", "message": "Data refresh started in background. Check /api/data/status for progress."}
    else:
        result = run_full_refresh(current_year=2025, retrain=True)
        return result


@router.post("/data/import/players")
async def import_players_csv(file: UploadFile = File(...)) -> dict[str, object]:
    """
    Import a real player CSV export (e.g. downloaded directly from BartTorvik).

    The CSV must have at minimum: player_name, ts_pct, usage_rate, previous_bpm.
    All other columns are optional and defaulted.

    Steps:
      1. Parse the uploaded CSV
      2. Normalize column names (handles BartTorvik, BBRef, and KenPom exports)
      3. Save to players.csv and players DB table
      4. Refresh the in-memory player cache
      5. Retrain ML models on the new data
    """
    from app.config import DATA_DIR
    from app.data_pipeline.builder import build_portal_board
    from app.db import initialize_database
    from app.services.ml_registry import train_pipeline
    from app.services.repository import refresh_cache

    content = await file.read()
    try:
        df = pd.read_csv(StringIO(content.decode("utf-8", errors="replace")))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {exc}")

    # Normalize common column name variants from different export sources
    col_map = {
        "Player": "player_name", "Team": "school", "Conf": "conference",
        "TS%": "ts_pct", "Usg": "usage_rate", "Ortg": "offensive_rating",
        "Drtg": "defensive_rating", "Ast%": "assist_rate", "TO%": "turnover_rate",
        "OR%": "off_rebound_rate", "DR%": "def_rebound_rate",
        "Stl%": "steal_rate", "Blk%": "block_rate", "adBPM": "bpm",
        "BPM": "bpm", "VORP": "vorp", "3P%": "three_pt_pct", "FT%": "ft_pct",
        "Ppg": "ppg", "Rpg": "rpg", "Apg": "apg", "GP": "games", "Min%": "minutes_pct",
        "Yr": "class", "HGT": "height", "Wt": "weight", "Pos": "position",
        "USG%": "usage_rate", "AST%": "assist_rate", "STL%": "steal_rate",
        "BLK%": "block_rate", "TOV%": "turnover_rate", "ORB%": "off_rebound_rate",
        "DRB%": "def_rebound_rate", "School": "school",
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    if "player_name" not in df.columns:
        raise HTTPException(status_code=400, detail="CSV must contain a player name column ('Player' or 'player_name').")

    # Map bpm to previous_bpm if needed
    if "bpm" in df.columns and "previous_bpm" not in df.columns:
        df["previous_bpm"] = df["bpm"]

    portal_board = build_portal_board(df)
    portal_board.to_csv(DATA_DIR / "players.csv", index=False)

    initialize_database()
    refresh_cache()

    # Retrain if we have enough rows
    hist_path = DATA_DIR / "historical_transfers.csv"
    if hist_path.exists():
        hist = pd.read_csv(hist_path)
        if len(hist) >= 50:
            train_pipeline(hist)

    return {
        "status": "imported",
        "rows_imported": len(portal_board),
        "columns": list(portal_board.columns),
        "message": "Players imported and ML models retrained. Check /api/data/status for model performance.",
    }


@router.post("/data/import/historical")
async def import_historical_csv(file: UploadFile = File(...)) -> dict[str, object]:
    """
    Import a historical transfers CSV to retrain the ML model.

    Required columns: player_name, previous_bpm, future_bpm, ts_pct, usage_rate.
    The more rows, the better the model.  At least 100 rows recommended.
    """
    from app.config import DATA_DIR
    from app.services.ml_registry import train_pipeline
    from app.services.repository import refresh_cache

    content = await file.read()
    try:
        df = pd.read_csv(StringIO(content.decode("utf-8", errors="replace")))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {exc}")

    required = {"previous_bpm", "future_bpm", "ts_pct", "usage_rate"}
    missing = required - set(df.columns)
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required columns: {missing}")

    df.to_csv(DATA_DIR / "historical_transfers.csv", index=False)
    train_pipeline(df)
    refresh_cache()

    perf = get_pipeline().get_model_performance()
    return {
        "status": "trained",
        "rows_trained_on": len(df),
        "model_performance": perf,
        "message": "Historical data saved and ML ensemble retrained on your real data.",
    }


@router.get("/agents")
def list_agents() -> dict[str, object]:
    agents = [
        {"id": "main", "name": "Front Office AI", "emoji": "🏀", "tagline": "Your central basketball operations assistant"},
        {"id": "recruiting", "name": "Recruiting Agent", "emoji": "🎯", "tagline": "Ranked, explainable recruiting boards"},
        {"id": "transfer-portal", "name": "Transfer Portal Agent", "emoji": "🔄", "tagline": "Fast, explainable portal decisions"},
        {"id": "scenario", "name": "Scenario Agent", "emoji": "♟️", "tagline": "Simulate roster moves before committing"},
        {"id": "hidden-gem", "name": "Hidden Gem Agent", "emoji": "💎", "tagline": "Find players before the market does"},
        {"id": "roster-builder", "name": "Roster Builder Agent", "emoji": "🏗️", "tagline": "Build a complete Illinois roster plan"},
        {"id": "scouting", "name": "Scouting Agent", "emoji": "📋", "tagline": "Instant scouting reports and opponent prep"},
        {"id": "player-development", "name": "Player Development Agent", "emoji": "📈", "tagline": "Data-backed individual development plans"},
        {"id": "compare", "name": "Compare Players Agent", "emoji": "⚖️", "tagline": "Side-by-side player decisions"},
        {"id": "risk-fit", "name": "Risk & Fit Agent", "emoji": "🛡️", "tagline": "Clear, explainable risk assessment"},
        {"id": "market-inefficiency", "name": "Market Inefficiency Agent", "emoji": "📊", "tagline": "Find value before the market prices it in"},
        {"id": "game-plan", "name": "Game Plan Agent", "emoji": "🎮", "tagline": "Fast, usable opponent and matchup prep"},
    ]
    return {"agents": agents, "count": len(agents)}


@router.get("/data-sources")
def data_sources() -> dict[str, object]:
    return {"sources": DATA_META}


@router.get("/players")
def players(
    limit: int = Query(default=50, ge=1, le=200),
    position: str | None = None,
    conference: str | None = None,
) -> dict[str, object]:
    data = get_players_enriched()
    board = data.copy()
    if position:
        board = board[board["position"] == position]
    if conference:
        board = board[board["conference"] == conference]
    board = board.sort_values("hidden_gem_score", ascending=False).head(limit)
    return {"items": board.to_dict("records"), "count": len(board), "data_source": get_meta("players")}


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    players = get_players_enriched()
    roster = get_illinois_roster()
    result = chat_response(payload.message, players, roster, agent_id=payload.agent_id)

    # Extract routed_agent_id from answer prefix if present
    routed_id: str | None = None
    answer = result.answer
    if answer.startswith("AGENT_SWITCH:"):
        first_line, _, rest = answer.partition("\n")
        routed_id = first_line.replace("AGENT_SWITCH:", "").strip()
        answer = rest  # strip the AGENT_SWITCH prefix from the displayed answer

    return ChatResponse(answer=answer, evidence=result.evidence, navigation=result.navigation, routed_agent_id=routed_id)


@router.get("/roster/illinois")
def illinois_roster_endpoint() -> dict[str, object]:
    """Return the real 2026-27 Illinois Men's Basketball roster."""
    roster = get_illinois_roster()
    return {
        "players": roster.to_dict("records"),
        "count": len(roster),
        "data_source": get_meta("illinois_roster"),
    }


@router.post("/recruiting/targets")
def recruiting_targets(query: RecruitingQuery) -> dict[str, object]:
    players_df = get_players_enriched()
    roster_df = get_illinois_roster()
    board = rank_targets(
        players_df,
        position=query.position,
        min_height=query.min_height,
        conference=query.conference,
        max_risk=query.max_risk,
        min_shooting=query.min_shooting,
        min_defense=query.min_defense,
        min_rebounding=query.min_rebounding,
        min_playmaking=query.min_playmaking,
    )

    _bpm_col = "predicted_bpm" if "predicted_bpm" in board.columns else "projected_impact_score"
    hidden = board.sort_values("market_inefficiency_score", ascending=False).head(10)
    value = board.sort_values(["transfer_success_score", "public_transfer_rank"], ascending=[False, True]).head(10)
    upside = board.sort_values([_bpm_col, "risk_score"], ascending=[False, True]).head(10)

    gm_priority = board.copy()
    gm_priority["gm_priority_score"] = (
        0.34 * gm_priority["illinois_fit_score"]
        + 0.28 * gm_priority["projected_impact_score"]
        + 0.2 * gm_priority["market_inefficiency_score"]
        + 0.18 * (100 - gm_priority["risk_score"])
    )
    gm_priority = gm_priority.sort_values("gm_priority_score", ascending=False).head(12)

    org_fit = board.sort_values(["illinois_fit_score", "transfer_success_score"], ascending=False).head(12)
    safe_floor = board.sort_values(["risk_score", "illinois_fit_score"], ascending=[True, False]).head(12)
    swing_bets = board.sort_values([_bpm_col, "risk_score"], ascending=[False, False]).head(12)

    wing_defenders = players_df[players_df["position"].isin(["WI", "PF"])].sort_values(
        ["steal_rate", "block_rate", "defensive_rating", "illinois_fit_score"],
        ascending=[False, False, True, False],
    ).head(8)
    lead_guards = players_df[players_df["position"].isin(["PG", "G", "PU"])].sort_values(
        ["assist_rate", "turnover_rate", "illinois_fit_score"],
        ascending=[False, True, False],
    ).head(8)
    stretch_bigs = players_df[players_df["position"].isin(["PF", "C"])].sort_values(
        ["three_pt_pct", "ts_pct", "illinois_fit_score"],
        ascending=[False, False, False],
    ).head(8)
    rim_protectors = players_df[players_df["position"].isin(["C", "PF"])].sort_values(
        ["block_rate", "def_rebound_rate", "defensive_rating"],
        ascending=[False, False, True],
    ).head(8)

    public_overvalued = players_df.copy()
    public_overvalued["overvalued_risk_score"] = (
        0.5 * (100 - public_overvalued["market_inefficiency_score"])
        + 0.3 * public_overvalued["risk_score"]
        + 0.2 * (100 - public_overvalued["illinois_fit_score"])
    )
    public_overvalued = public_overvalued.sort_values("overvalued_risk_score", ascending=False).head(8)

    roster_need_flags: list[str] = []
    if roster_df["three_pt_pct"].mean() < 0.345:
        roster_need_flags.append("Need more reliable high-volume perimeter shooting.")
    if roster_df["assist_rate"].mean() < 15:
        roster_need_flags.append("Need secondary creation and lower-turnover guard play.")
    if roster_df["defensive_rating"].mean() > 100:
        roster_need_flags.append("Need stronger point-of-attack defense and rim support.")
    if not roster_need_flags:
        roster_need_flags.append("Roster profile is balanced; prioritize best-value impact talent.")

    summary_metrics = {
        "avg_fit_top_targets": round(float(board.head(10)["illinois_fit_score"].mean()), 2),
        "avg_risk_top_targets": round(float(board.head(10)["risk_score"].mean()), 2),
        "avg_hidden_gem_top_targets": round(float(board.head(10)["hidden_gem_score"].mean()), 2),
        "avg_projected_impact_top_targets": round(float(board.head(10)["projected_impact_score"].mean()), 2),
    }

    return {
        "top_targets": board.head(10).to_dict("records"),
        "top_hidden_gems": hidden.to_dict("records"),
        "top_value_players": value.to_dict("records"),
        "top_high_upside_players": upside.to_dict("records"),
        "gm_priority_board": gm_priority.to_dict("records"),
        "organization_fit_board": org_fit.to_dict("records"),
        "safe_floor_board": safe_floor.to_dict("records"),
        "swing_bets_board": swing_bets.to_dict("records"),
        "role_boards": {
            "wing_defenders": wing_defenders.to_dict("records"),
            "lead_guards": lead_guards.to_dict("records"),
            "stretch_bigs": stretch_bigs.to_dict("records"),
            "rim_protectors": rim_protectors.to_dict("records"),
        },
        "overvalued_risk_board": public_overvalued.to_dict("records"),
        "illinois_roster_needs": roster_need_flags,
        "summary_metrics": summary_metrics,
    }


@router.get("/player/{player_name}")
def player_intelligence(player_name: str) -> dict[str, object]:
    players_df = get_players_enriched()
    match = players_df[players_df["player_name"].str.lower() == player_name.lower()]
    if match.empty:
        raise HTTPException(status_code=404, detail="Player not found")

    player = match.iloc[0]
    comps = compute_similarity(players_df, player["player_name"], top_n=6)
    dims = {
        "shooting": float(player["three_pt_pct"] * 100),
        "playmaking": float(max(1, player["assist_rate"] - player["turnover_rate"] + 50)),
        "defense": float((112 - player["defensive_rating"]) * 2.2 + player["steal_rate"] * 4 + player["block_rate"] * 3),
        "rebounding": float((player["off_rebound_rate"] + player["def_rebound_rate"]) * 2.2),
        "efficiency": float(player["ts_pct"] * 100),
        "fit": float(player["illinois_fit_score"]),
    }

    strengths = sorted(dims.items(), key=lambda x: x[1], reverse=True)[:3]
    weaknesses = sorted(dims.items(), key=lambda x: x[1])[:2]

    report = {
        "player": player.to_dict(),
        "radar": dims,
        "archetype": player["archetype"],
        "comparable_players": comps.to_dict("records"),
        "strengths": [f"{name.title()} grades at {value:.1f}." for name, value in strengths],
        "weaknesses": [f"{name.title()} is currently {value:.1f}; development needed." for name, value in weaknesses],
        "ai_scouting_report": (
            f"{player['player_name']} projects as a {player['archetype']} with transfer success score "
            f"{player['transfer_success_score']:.1f}. Illinois fit is {player['illinois_fit_score']:.1f} with risk {player['risk_score']:.1f}."
        ),
    }
    return report


@router.get("/hidden-gem-lab")
def hidden_gem_lab() -> dict[str, object]:
    players_df = get_players_enriched()
    ranked = players_df.sort_values("market_inefficiency_score", ascending=False)
    overrated = players_df.sort_values("market_inefficiency_score", ascending=True)

    return {
        "top_hidden_gems": ranked.head(15).to_dict("records"),
        "top_underrated_players": ranked.head(15).to_dict("records"),
        "top_overrated_players": overrated.head(15).to_dict("records"),
        "rank_vs_impact": players_df[["player_name", "public_transfer_rank", "projected_impact_score", "market_inefficiency_score"]].to_dict("records"),
    }


@router.post("/roster-builder")
def roster_builder(payload: RosterRequest) -> dict[str, object]:
    players_df = get_players_enriched()
    selected = players_df[players_df["player_name"].isin(payload.selected_players)]
    if selected.empty:
        selected = players_df.sort_values("illinois_fit_score", ascending=False).head(5)

    outcomes = roster_outcomes(selected)
    return {
        "selected_players": selected.to_dict("records"),
        "roster_analysis": outcomes,
        "strengths": [
            f"Spacing profile projects at {outcomes['spacing_score']:.1f}.",
            f"Defensive score projects at {outcomes['defensive_score']:.1f}.",
            f"Team identity: {outcomes['team_identity']}.",
        ],
        "weaknesses": [
            f"Risk score currently averages {outcomes['risk_score']:.1f}.",
            "Role redundancy should be checked against current Illinois rotation minutes.",
        ],
    }


@router.get("/scouting/{player_name}", response_model=ScoutingReportResponse)
def scouting(player_name: str) -> ScoutingReportResponse:
    players_df = get_players_enriched()
    match = players_df[players_df["player_name"].str.lower() == player_name.lower()]
    if match.empty:
        raise HTTPException(status_code=404, detail="Player not found")

    p = match.iloc[0]

    # --- Plain-English scouting language ---
    _3pt = float(p["three_pt_pct"])
    _ts  = float(p["ts_pct"])
    _ast = float(p["assist_rate"])
    _to  = float(p["turnover_rate"])
    _drtg = float(p["defensive_rating"])
    _fit  = float(p["illinois_fit_score"])
    _risk = float(p["risk_score"])
    _ppg  = float(p.get("ppg", 0))
    _rpg  = float(p.get("rpg", 0) if p.get("rpg") is not None else 0)
    _apg  = float(p.get("apg", 0) if p.get("apg") is not None else 0)

    # Fit verdict
    if _fit >= 65:
        fit_verdict = f"Strong fit for Underwood's system ({_fit:.0f}/100) — hits the key thresholds for shooting, defense, and playmaking."
    elif _fit >= 50:
        fit_verdict = f"Moderate fit ({_fit:.0f}/100) — matches some of Illinois's needs but has gaps. Worth a call but needs role clarification."
    else:
        fit_verdict = f"Likely a system mismatch ({_fit:.0f}/100) — profile doesn't line up well with Underwood's three-point heavy, switching defense scheme."

    # Risk verdict
    if _risk < 35:
        risk_verdict = f"Low risk ({_risk:.0f}/100 — lower is safer). Clean profile. Minimal production concerns going into this portal cycle."
    elif _risk < 55:
        risk_verdict = f"Moderate risk ({_risk:.0f}/100). Main flags: review turnover discipline and whether his role translates from {p['conference']} to Big Ten physicality."
    else:
        risk_verdict = f"Elevated risk ({_risk:.0f}/100). Staff should do full diligence on role expectations, minutes history, and conference translation before offering."

    # Shooting context
    if _3pt >= 0.40:
        shooting_str = f"Elite shooter — {_3pt:.1%} from three. Well above Illinois's 36.5% system target. Creates real spacing."
    elif _3pt >= 0.365:
        shooting_str = f"Reliable shooter — {_3pt:.1%} from three. Meets Illinois's minimum spacing threshold. Should command defensive attention."
    elif _3pt >= 0.33:
        shooting_str = f"Serviceable shooter — {_3pt:.1%} from three. Slightly below Illinois's threshold; defenders can sag off him in some lineups."
    else:
        shooting_str = f"Shooting concern — {_3pt:.1%} from three. Below Illinois's 36.5% threshold. Would need scheme adjustment or a non-shooting role."

    # Efficiency context
    if _ts >= 0.60:
        eff_str = f"Highly efficient scorer — {_ts:.1%} true shooting. Gets good looks and converts them. Won't waste possessions."
    elif _ts >= 0.55:
        eff_str = f"Solid shooting efficiency — {_ts:.1%} true shooting. Efficient enough to run through Underwood's action-heavy offense."
    else:
        eff_str = f"Below-average efficiency — {_ts:.1%} true shooting. Will need to get easier looks in a structured offense to improve this."

    # Defense context
    if _drtg <= 96:
        def_str = f"Excellent defender — {_drtg:.0f} defensive rating. Holds opponents to under a point per possession when on the floor. Underwood will love this."
    elif _drtg <= 102:
        def_str = f"Solid defender — {_drtg:.0f} defensive rating. Capable in Illinois's switching scheme."
    elif _drtg <= 108:
        def_str = f"Average defense — {_drtg:.0f} defensive rating. Not a liability, but confirm with film that he can handle Big Ten perimeter threats."
    else:
        def_str = f"Defensive concern — {_drtg:.0f} defensive rating. This is above the threshold for Illinois's switching defense. Needs film validation."

    # Playmaking
    if _ast >= 20:
        play_str = f"High-level playmaker — {_ast:.1f}% assist rate. Creates for teammates at a level that runs Underwood's pick-and-roll system well."
    elif _ast >= 14:
        play_str = f"Capable playmaker — {_ast:.1f}% assist rate. Can run secondary actions and share the ball in an up-tempo system."
    else:
        play_str = f"Limited playmaking — {_ast:.1f}% assist rate. More of a scorer/role player; won't be asked to initiate offense."

    # Turnover risk
    if _to > 18:
        to_str = f"Turnover-prone — {_to:.1f}% turnover rate. High risk in Illinois's fast pace. Every turnover is a free transition opportunity for opponents."
    elif _to > 14:
        to_str = f"Average ball security — {_to:.1f}% turnover rate. Manageable but watch situational decision-making under pressure."
    else:
        to_str = f"Excellent ball security — {_to:.1f}% turnover rate. Protects possessions, which Underwood's system depends on."

    # Recruiting tier
    if _fit >= 65 and _risk < 40:
        rec = f"TIER 1 — Call immediately. Strong system fit, low risk, and a profile that solves one of Illinois's known needs. Scholarship offer is justified."
    elif _fit >= 50 and _risk < 55:
        rec = f"TIER 2 — Schedule a visit. Solid fit with manageable risk. Needs a conversation about role expectations before committing a scholarship."
    elif _risk < 60:
        rec = f"TIER 3 — Monitor and revisit. Some fit concerns but worth staying in contact. Reassess if Illinois's other targets fall through."
    else:
        rec = f"AVOID for now — risk profile and fit concerns don't justify a scholarship at this stage. Keep on radar only if circumstances change significantly."

    # Development areas based on weaknesses
    dev = []
    if _3pt < 0.365: dev.append("3-point shooting consistency (needs to hit 36.5%+ to stay on the floor in Underwood's offense)")
    if _to > 16:     dev.append("turnover discipline under defensive pressure in up-tempo situations")
    if _drtg > 104:  dev.append("on-ball and help defense in Big Ten switching schemes")
    if not dev:      dev.append("position-specific refinement and Big Ten conditioning readiness")

    report = ScoutingReportResponse(
        player_name=p["player_name"],
        executive_summary=(
            f"{p['player_name']} — {p.get('position', '?')}, {p.get('school', '?')} ({p.get('conference', '?')})\n"
            f"2024-25 stats: {_ppg:.1f} PPG / {_rpg:.1f} RPG / {_apg:.1f} APG | {_3pt:.1%} 3PT | {_ts:.1%} TS%\n\n"
            f"{fit_verdict}\n\n{risk_verdict}"
        ),
        strengths=f"{shooting_str}\n\n{eff_str}\n\n{play_str}",
        weaknesses=f"{def_str}\n\n{to_str}",
        projected_role=(
            f"Projects as a {p['archetype'].lower()} in a Big Ten rotation. "
            f"{'Starter upside' if float(p['transfer_success_score']) >= 70 else 'Quality rotation player' if float(p['transfer_success_score']) >= 50 else 'Depth/developmental role'}."
        ),
        development_areas="Priority development areas: " + "; ".join(dev) + ".",
        illinois_fit=fit_verdict,
        recruiting_recommendation=rec,
        coach_notes=(
            f"Film focus: {"3-point shot mechanics and off-ball movement" if _3pt < 0.365 else "defensive rotation in switching schemes"}. "
            f"In film sessions, prioritize: (1) late-shot-clock creation, (2) defensive assignment reads against Big Ten size, "
            f"(3) transition decision-making. "
            f"Ask in conversation: role expectations, minutes commitment, NIL tier, and timeline to decision."
        ),
    )
    return report


@router.get("/scouting/{player_name}/pdf")
def scouting_pdf(player_name: str) -> Response:
    report = scouting(player_name)
    pdf_bytes = build_scouting_pdf(player_name, report.model_dump())
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={player_name.replace(' ', '_')}_scouting_report.pdf"},
    )


@router.get("/predict/model-performance")
def predict_model_performance() -> dict[str, object]:
    ensure_models_trained()
    return get_pipeline().get_model_performance()


@router.get("/predict/{player_name}", response_model=PredictionResponse)
def predict(player_name: str) -> PredictionResponse:
    ensure_models_trained()
    players_df = get_players_enriched()
    match = players_df[players_df["player_name"].str.lower() == player_name.lower()]
    if match.empty:
        raise HTTPException(status_code=404, detail="Player not found")
    pred = get_pipeline().predict_player(match)
    return PredictionResponse(**pred)


@router.post("/compare")
def compare_players(payload: CompareRequest) -> dict[str, object]:
    players_df = get_players_enriched()
    p1 = players_df[players_df["player_name"].str.lower() == payload.player_a.lower()]
    p2 = players_df[players_df["player_name"].str.lower() == payload.player_b.lower()]
    if p1.empty or p2.empty:
        raise HTTPException(status_code=404, detail="One or both players not found")

    a = p1.iloc[0]
    b = p2.iloc[0]
    score_a = 0.45 * a["illinois_fit_score"] + 0.35 * a["transfer_success_score"] - 0.2 * a["risk_score"]
    score_b = 0.45 * b["illinois_fit_score"] + 0.35 * b["transfer_success_score"] - 0.2 * b["risk_score"]
    winner = a if score_a >= score_b else b

    return {
        "player_a": a.to_dict(),
        "player_b": b.to_dict(),
        "recommendation": (
            f"{winner['player_name']} is the stronger Illinois fit due to better combined fit, projected impact, and risk-adjusted profile."
        ),
        "advantages": {
            "player_a": [
                f"Fit score {a['illinois_fit_score']:.1f}",
                f"3P {a['three_pt_pct']:.1%}",
                f"Defensive rating {a['defensive_rating']:.1f}",
            ],
            "player_b": [
                f"Fit score {b['illinois_fit_score']:.1f}",
                f"3P {b['three_pt_pct']:.1%}",
                f"Defensive rating {b['defensive_rating']:.1f}",
            ],
        },
    }


@router.get("/insights")
def insights() -> dict[str, object]:
    players_df = get_players_enriched()
    cards = front_office_insights(players_df)

    special_targets = {
        "most_similar_to_terrence_shannon_jr": compute_similarity(players_df, players_df.iloc[0]["player_name"], top_n=1).to_dict("records"),
        "most_similar_to_kasparas_jakucionis": compute_similarity(players_df, players_df.iloc[1]["player_name"], top_n=1).to_dict("records"),
        "most_similar_to_current_illinois_needs": players_df.sort_values(["illinois_fit_score", "risk_score"], ascending=[False, True]).head(3).to_dict("records"),
    }
    return {"insights": cards, "special_targets": special_targets}


@router.get("/methodology")
def methodology() -> dict[str, object]:
    return {
        "problem": "College staffs need fast, evidence-based transfer portal decisions under tight timelines.",
        "data": "Public style transfer stats plus engineered roster context features in SQLite.",
        "features": [
            "Scoring efficiency (TS, 3P, FT)",
            "Playmaking and turnover control",
            "Rebounding profile",
            "Defensive event rates and ratings",
            "Market signal from public transfer ranking",
        ],
        "models": ["Random Forest Regressor", "Random Forest Classifier", "XGBoost (if installed)", "KMeans Archetype Clustering", "Cosine Similarity Engine"],
        "scoring": ["Transfer Success Score", "Illinois Fit Score", "Risk Score", "Hidden Gem Score", "Market Inefficiency Score"],
        "limitations": [
            "Sample data is synthetic and for demonstration only.",
            "No injury/medical/NIL variables in current model.",
            "Contextual scheme fit still requires film and staff expertise.",
        ],
        "future_work": [
            "Integrate real portal APIs and play-type data.",
            "Add lineup simulation by pace and shot profile.",
            "Track recruiting funnel stages and outcomes over time.",
        ],
        "why_useful": "Transforms large transfer pools into role-specific, evidence-backed recruiting decisions for coaching staffs.",
    }
