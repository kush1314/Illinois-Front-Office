from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from app.config import get_settings
from app.services.analytics import compute_similarity, front_office_insights, roster_outcomes
from app.services.ml_registry import ml_predict

# ── Metric explanations referenced by chatbot ────────────────────────────────
GLOSSARY: dict[str, str] = {
    "transfer translation score": (
        "Transfer Translation Score (0-100): estimates how likely a player's current production profile is to "
        "carry over into a useful Illinois rotation role. Inputs: efficiency (TS%), prior BPM, usage rate, "
        "conference strength, rebounding, and playmaking. 70+ = strong translation likely. 50-70 = moderate "
        "— role and competition level need film confirmation. Under 50 = meaningful production risk. "
        "This is a prototype scoring model, not a live recruiting model. Treat it as a research filter, "
        "not a final decision."
    ),
    "illinois fit score": (
        "Illinois Fit Score (0-100): how well a player's skill profile matches what Brad Underwood's "
        "system actually needs — up-tempo offense, 3-point volume, perimeter switching defense, playmaking "
        "from guards, and wing versatility. Weights: 3PT% (above 36.5% threshold), defensive rating, "
        "assist rate, efficiency. 65+ = strong system match. 50-65 = fits some needs, gaps elsewhere. "
        "Under 50 = likely a system mismatch unless a specific role is available."
    ),
    "hidden gem score": (
        "Hidden Gem Score (0-100): flags players where our scoring model rates them significantly higher "
        "than their dataset rank. A high Hidden Gem Score means strong production and fit metrics relative "
        "to where the player shows up in standard rankings. It does NOT mean the player is secretly elite — "
        "it means they may be undervalued relative to their metrics. Always verify with film before acting."
    ),
    "risk score": (
        "Risk Score (0-100, LOWER IS SAFER): penalizes players for small sample size (under 20 games), "
        "high turnover rate (over 18%), poor free-throw shooting (under 70%), inefficient scoring "
        "(TS% under 50%), and extreme usage mismatch. Under 35 = low risk. 35-55 = moderate risk — "
        "review role expectations. Over 55 = elevated risk — needs strong fit or upside to justify."
    ),
    "projected bpm": (
        "Projected BPM at Illinois (Box Plus/Minus per 100 possessions): the ML ensemble's estimate of "
        "the player's net impact per 100 possessions in a Big Ten rotation. Context: an average Big Ten "
        "starter is roughly 0 BPM. +2 BPM = solid rotation contributor. +4+ = potential star. "
        "Negative = depth-level player or role mismatch. The model was trained on synthetic data calibrated "
        "to NCAA distributions — treat as a directional estimate, not a guarantee."
    ),
    "dataset rank": (
        "Dataset Rank / Market Rank: a sequential rank field (1-150) in our prototype dataset representing "
        "approximate consensus market attention. Rank #1 = highest-profile target in the dataset, "
        "#150 = lowest-profile. This is NOT from ESPN, Rivals, On3, or any live recruiting service. "
        "It is a prototype field used to model market inefficiency for demonstration purposes."
    ),
    "bpm": (
        "BPM (Box Plus/Minus): a basketball analytics metric estimating a player's contribution to their "
        "team per 100 possessions, adjusted for competition. Positive = above-average contributor. "
        "Zero = average. Negative = below-average. Prior BPM (last season) is the strongest single "
        "predictor of future production in the scoring model."
    ),
    "value gap score": (
        "Value Gap Score / Market Inefficiency Score (0-100): the gap between where our model ranks "
        "a player (Illinois Fit + Translation Score) versus where the dataset's market rank places them. "
        "High score = the model sees more value than the market does. This is the core 'hidden gem' signal. "
        "Act quickly on high-gap players before competing programs identify the same inefficiency."
    ),
    "rotation impact score": (
        "Rotation Impact Score (0-100): a composite estimate of a player's overall production ceiling "
        "in an Illinois-level rotation, combining Transfer Translation Score, projected BPM, and "
        "Illinois Fit Score. 70+ = likely rotation contributor or starter. 50-70 = quality depth. "
        "Under 50 = developmental or situational use."
    ),
    "ts%": (
        "TS% (True Shooting Percentage): the most accurate single shooting efficiency metric. Accounts "
        "for 2-pointers, 3-pointers, and free throws together. Formula: points / (2 × (FGA + 0.44 × FTA)). "
        "55%+ = efficient. 60%+ = elite. Illinois targets: 55%+ preferred for perimeter players, "
        "58%+ for high-usage guards."
    ),
    "ast/to": (
        "Assist Rate / Turnover Rate: playmaking quality indicators. Assist Rate = % of teammate FGs "
        "assisted on while player is on floor. Turnover Rate = % of possessions ending in a turnover. "
        "Illinois system wants high assist rate (16%+) with low turnover rate (under 15%) for guards."
    ),
    "usage rate": (
        "Usage Rate: % of team possessions used by the player while on the floor (shots, free throws, "
        "turnovers). 20-25% = standard rotation player. 25-30% = featured player. 30%+ = primary option. "
        "Context: a player with 25% usage at a mid-major who scores efficiently may not maintain that "
        "role at Illinois — it's a key risk factor in the Transfer Translation model."
    ),
}

DATA_TRANSPARENCY = {
    "are these real players": (
        "Yes — the player stats are real 2024-25 NCAA Division I statistics scraped from "
        "Sports Reference (sports-reference.com/cbb). The dataset includes 200 players from "
        "27 schools including Cooper Flagg (Duke), Johni Broome (Auburn), Braden Smith (Purdue), "
        "Hunter Dickinson (Kansas), Walter Clayton Jr. (Florida), and others.\n\n"
        "Important caveat: these are the 2024-25 season stats for these players — "
        "portal eligibility status is NOT tracked. The dataset does not guarantee that every "
        "player listed has entered or will enter the transfer portal. The tool models portal "
        "decisions based on their statistical profiles.\n\n"
        "Illinois roster data is from the real 2024-25 Illinois season: Jakucionis, T. Ivisic, "
        "Will Riley, Kylan Boswell, Tre White, and others.\n\n"
        "The ML training dataset (3,000 records) is still synthetic historical transfer data "
        "calibrated to NCAA distributions — not verified real-world transfer outcomes."
    ),
    "data source": (
        "Player statistics: scraped from Sports Reference (sports-reference.com/cbb) — "
        "real 2024-25 NCAA Division I per-game statistics. Covers 200 players from 27 schools "
        "across Big Ten, SEC, Big 12, and ACC conferences.\n\n"
        "Illinois roster: real 2024-25 Illinois season data (Jakucionis, T. Ivisic, Riley, Boswell, White).\n\n"
        "BPM shown in this tool is an APPROXIMATION calculated from per-game stats "
        "(TS%, scoring, rebounds, assists, steals, blocks, turnovers). Sports Reference's "
        "official BPM requires team-level possession data not available in the per-game tables.\n\n"
        "ML training data: 3,000 synthetic transfer outcome profiles calibrated to NCAA distributions. "
        "Not verified real-world labeled outcomes. Model is a functional prototype."
    ),
    "player count": (
        "The dataset contains 200 real D1 players from 27 schools — this reflects the "
        "Sports Reference rate-limiting encountered during scraping (10 requests per minute). "
        "A production version would use scheduled overnight scraping to pull all 300+ D1 schools. "
        "The current 200 players are drawn from the Big Ten, SEC, Big 12, and ACC — the most "
        "relevant conferences for Illinois recruiting."
    ),
    "model real": (
        "The Random Forest + XGBoost + Neural Network ensemble is a real trained ML architecture "
        "running on the backend. The Transfer Translation Score it produces is a genuine ML prediction. "
        "However, it was trained on 3,000 synthetic transfer outcome profiles — not a verified "
        "dataset of real historical transfers with documented outcomes. The model architecture "
        "and prediction pipeline are production-quality; the training data quality is prototype-level. "
        "BPM forecasts should be treated as directional estimates, not precise predictions."
    ),
}

ILLINOIS_CONTEXT = {
    "coach": "Brad Underwood",
    "system": "Up-tempo, 3-point heavy offense with switching man defense. High pace, high usage for primary creators. Prioritizes length and versatility on the perimeter.",
    "style_priorities": ["3-point shooting", "perimeter switching defense", "playmaking guards", "versatile wings"],
    "known_needs_2026": [
        "A reliable 3-and-D wing who can guard 1-through-3",
        "A secondary ball handler who protects possessions (low TO rate)",
        "A stretch big (4/5) who can shoot from mid-range and beyond",
    ],
    "fit_profile": {
        "3pt_threshold": 0.365,
        "assist_rate_min": 16.0,
        "def_rating_max": 100.5,
        "risk_max": 55,
    },
    "returning_strengths": [
        "Andrej Stojakovic — elite perimeter shooter, system fit",
        "Zvonimir Ivisic — interior anchor, elite post defense",
        "Tomislav Ivisic — rim presence, rebounding",
    ],
}

AGENT_DESCRIPTIONS = {
    "main": (
        "I'm the Illinois Front Office AI — a central basketball operations assistant. "
        "Tell me what you need and I'll route you to the right specialist, or just answer directly. "
        "I can handle recruiting boards, player comparisons, scouting reports, portal ML rankings, hidden gems, roster construction, risk assessments, and more.\n\n"
        "Try asking something like:\n"
        "- 'Who should Illinois prioritize in the portal?'\n"
        "- 'Find me a 3-and-D wing'\n"
        "- 'Compare Ivan White and Henry Wilson'\n"
        "- 'What are Illinois's biggest roster needs?'"
    ),
    "recruiting": (
        "I'm the Recruiting Agent. I build Illinois-specific transfer target boards tuned to Brad Underwood's system.\n\n"
        "Here's what I can do:\n"
        "- Generate tiered recruiting boards (Tier 1 = contact immediately, Tier 2 = schedule visits, Tier 3 = monitor)\n"
        "- Filter by role: 3-and-D wings, playmaking guards, stretch bigs, rim protectors\n"
        "- Flag which targets fit Illinois's 36.5% 3PT threshold and switching defense\n"
        "- Identify safe-floor targets vs. high-upside risks\n"
        "- Show what the market is overpaying for\n\n"
        "Try: 'Show me the recruiting board' or 'Find a low-risk guard for Underwood's system'"
    ),
    "transfer-portal": (
        "I'm the Transfer Portal Agent. I use a Random Forest + XGBoost + Neural Network ensemble trained on 3,000 historical transfer outcomes to rank portal targets by predicted BPM, success probability, and Illinois fit.\n\n"
        "What I can do:\n"
        "- Rank portal players by ML-predicted transfer success probability\n"
        "- Show projected BPM at Illinois for each player\n"
        "- Explain which features (prior BPM, conference upgrade, efficiency) drove each prediction\n"
        "- Identify players with high upside and manageable risk\n"
        "- Compare conference translation for players moving to the Big Ten\n\n"
        "Try: 'Who are the top ML-ranked portal targets?' or 'Show me high-ceiling transfers with under 40 risk'"
    ),
    "hidden-gem": (
        "I'm the Hidden Gem Agent. I find portal players the market is undervaluing — people Illinois can move on before public consensus catches up.\n\n"
        "How I work:\n"
        "1. The ML ensemble predicts each player's future BPM and transfer success probability\n"
        "2. I compare that model rank against public consensus transfer rankings\n"
        "3. Players where the model ranks them significantly better = market inefficiency\n"
        "4. I weight that inefficiency with Illinois fit and risk scores to find the actual targets worth pursuing\n\n"
        "What I can do:\n"
        "- Surface the top hidden gems on the current board\n"
        "- Find small-school players with strong efficiency metrics who get overlooked\n"
        "- Flag players the public is overpaying for\n"
        "- Show the market inefficiency score for any player\n\n"
        "Try: 'Show me the hidden gems' or 'Who is the market sleeping on at the wing position?'"
    ),
    "scouting": (
        "I'm the Scouting Agent. I generate detailed scouting reports grounded in statistics and ML predictions for any player on the board.\n\n"
        "What I can produce:\n"
        "- Statistical profile: scoring, playmaking, defense, rebounding\n"
        "- ML-predicted BPM and success probability at Illinois\n"
        "- Strengths relative to Underwood's system requirements\n"
        "- Specific weaknesses and red flags\n"
        "- Illinois fit verdict (Strong/Moderate/System Mismatch)\n"
        "- Comparable players from the database\n"
        "- Staff recommendation and priority tier\n\n"
        "Try: 'Scout the top target' or 'Generate a scouting report for [player name]'"
    ),
    "roster-builder": (
        "I'm the Roster Builder Agent. I help Illinois construct a complete portal class against the current roster's profile.\n\n"
        "What I can do:\n"
        "- Map current roster strengths so you don't duplicate existing pieces\n"
        "- Show available portal depth at each position\n"
        "- Recommend specific players to fill each roster gap\n"
        "- Project the team identity after adding transfers\n"
        "- Estimate win impact from a target class\n\n"
        "Try: 'Build a 2026 roster plan' or 'What does Illinois need most in the portal?'"
    ),
    "compare": (
        "I'm the Compare Players Agent. I run side-by-side analysis of any two portal targets so you can make a data-backed decision.\n\n"
        "What I compare:\n"
        "- ML success probability and projected BPM for each\n"
        "- Illinois fit score head-to-head\n"
        "- Risk profile comparison\n"
        "- Key stat differentials (3P%, defensive rating, assist rate, etc.)\n"
        "- Clear recommendation: safer floor, higher upside, or better Illinois fit\n\n"
        "Try: 'Compare [Player A] and [Player B]' or 'Who's the better fit between two top guards?'"
    ),
    "risk-fit": (
        "I'm the Risk and Fit Agent. I break down exactly why a player is a risk or a fit for Illinois, beyond just raw scores.\n\n"
        "What I analyze:\n"
        "- Risk score breakdown: minutes volatility, turnover rate, FT% discipline, usage mismatch\n"
        "- Illinois fit across Underwood's system requirements: shooting, defense, playmaking\n"
        "- Red flag detection: specific stats that indicate elevated risk\n"
        "- Safe floor targets with the lowest downside\n"
        "- High-upside players worth the additional risk\n\n"
        "Try: 'Show safe floor targets' or 'What are the red flags for [player name]?'"
    ),
    "player-development": (
        "I'm the Player Development Agent. I use ML-forecasted BPM ceilings and statistical profiles to map development priorities for each transfer target.\n\n"
        "What I can do:\n"
        "- Identify each player's highest-ceiling development path at Illinois\n"
        "- Point out specific statistical weaknesses to address in practice\n"
        "- Compare a player's profile against successful Illinois transfers\n"
        "- Estimate how much upside each player has relative to their current production\n\n"
        "Try: 'Who has the most development upside?' or 'What should [player name] work on at Illinois?'"
    ),
    "market-inefficiency": (
        "I'm the Market Inefficiency Agent. I find players Illinois can acquire before the broader market prices them correctly.\n\n"
        "How I work:\n"
        "- I compare ML model rankings against public consensus transfer rankings\n"
        "- A large positive gap = the model sees more value than the market does\n"
        "- I surface these players so Illinois can move first, before bidding wars start\n\n"
        "What I can show you:\n"
        "- The biggest value gaps on the current board\n"
        "- High-production players from low-visibility programs\n"
        "- Overranked players the public is overpaying for\n\n"
        "Try: 'Show the biggest market inefficiencies' or 'Find value in mid-major programs'"
    ),
    "scenario": (
        "I'm the Scenario Agent. I simulate roster moves before Illinois commits to them.\n\n"
        "What I can model:\n"
        "- 'What happens to team identity if we add a stretch big?'\n"
        "- Current depth by position and scholarship implications\n"
        "- Projected roster grade and win impact with different additions\n"
        "- Role redundancy checks against returning players\n\n"
        "Try: 'Simulate adding a rim protector' or 'What does our depth chart look like right now?'"
    ),
    "game-plan": (
        "I'm the Game Plan Agent. I use statistical profiles to prep for specific player matchups and opponent strategies.\n\n"
        "What I can do:\n"
        "- Identify the highest-impact offensive threats on the opposing roster\n"
        "- Recommend defensive assignments based on statistical tendencies\n"
        "- Flag players who excel in transition vs. half-court settings\n"
        "- Suggest offensive attack points based on opponent defensive weaknesses\n\n"
        "Try: 'Who are the biggest perimeter threats to defend?' or 'How should we attack their defense?'"
    ),
}

_META_TRIGGERS = {
    "how do you work", "how does this work", "how does this agent work",
    "what do you do", "what can you do", "explain yourself",
    "what is this", "what are you", "help me", "help",
    "what are your capabilities", "what can i ask", "how do i use this",
    "how do i use it", "explain", "tutorial", "what's this agent for",
    "what is this agent", "tell me about yourself", "who are you",
    "describe yourself", "what are you for", "what is this tool",
    "what is portalgpt", "what does this do", "what is this app",
}


def _is_meta_question(q: str) -> bool:
    ql = q.lower().strip()
    if ql in _META_TRIGGERS:
        return True
    if any(t in ql for t in [
        "how do you work", "how does this", "what can you",
        "tell me about", "explain how", "how are you different",
        "who are you", "what are you", "what is this", "how do i use",
    ]):
        return True
    return False


@dataclass
class ChatResult:
    answer: str
    evidence: list[dict[str, object]]
    navigation: list[dict[str, str]]


def _default_navigation() -> list[dict[str, str]]:
    # Single item — avoid overwhelming the user with too many buttons
    return [
        {"label": "Recruiting Center", "path": "/recruiting-center?focused=1", "reason": "See all portal targets ranked for Illinois."},
    ]


def _nav(agent_id: str) -> list[dict[str, str]]:
    routes = {
        "recruiting":         [("/recruiting-center?focused=1", "Full recruiting board with all filters.")],
        "transfer-portal":    [("/transfer-success-predictor?focused=1", "Full ML predictions and feature importance.")],
        "hidden-gem":         [("/hidden-gem-lab?focused=1", "Full market inefficiency analysis."), ("/recruiting-center?focused=1", "Turn hidden gems into contact priorities.")],
        "scouting":           [("/scouting-center?focused=1", "Full scouting report with PDF export.")],
        "roster-builder":     [("/roster-builder?focused=1", "Simulate full class construction with projections.")],
        "compare":            [("/compare-players?focused=1", "Interactive side-by-side comparison.")],
        "risk-fit":           [("/player-intelligence?focused=1", "Full risk and fit breakdown per player.")],
        "player-development": [("/player-intelligence?focused=1", "Full development profile per player.")],
        "market-inefficiency":[("/hidden-gem-lab?focused=1", "Deep market inefficiency analysis.")],
        "scenario":           [("/roster-builder?focused=1", "Build and simulate specific lineup combos.")],
        "game-plan":          [("/scouting-center?focused=1", "Full per-player scouting breakdown.")],
    }
    pairs = routes.get(agent_id, [])
    path_label = lambda p: p.split("?")[0].strip("/").replace("-", " ").title()
    return [{"label": path_label(path), "path": path, "reason": reason} for path, reason in pairs]


def _navigation_for_query(q: str) -> list[dict[str, str]]:
    if "compare" in q:
        return [
            {"label": "Compare Players", "path": "/compare-players?focused=1", "reason": "Run side-by-side fit and risk comparison."},
            {"label": "Player Intelligence", "path": "/player-intelligence?focused=1", "reason": "Deep dive each candidate before final call."},
        ]
    if "scouting" in q or "report" in q:
        return [
            {"label": "Scouting Center", "path": "/scouting-center?focused=1", "reason": "Generate executive scouting report."},
            {"label": "Player Intelligence", "path": "/player-intelligence?focused=1", "reason": "Review full metrics profile first."},
        ]
    if "roster" in q or "build" in q:
        return [
            {"label": "Roster Builder", "path": "/roster-builder?focused=1", "reason": "Model lineup construction and outcomes."},
            {"label": "Recruiting Center", "path": "/recruiting-center?focused=1", "reason": "Pull role-specific transfer candidates."},
        ]
    if "undervalued" in q or "hidden gem" in q or "value" in q or "market" in q:
        return [
            {"label": "Hidden Gem Lab", "path": "/hidden-gem-lab?focused=1", "reason": "Market inefficiency analysis."},
            {"label": "Recruiting Center", "path": "/recruiting-center?focused=1", "reason": "Turn inefficiencies into target board."},
        ]
    if "predict" in q or "success" in q or "probability" in q or "bpm" in q:
        return [
            {"label": "Transfer Success Predictor", "path": "/transfer-success-predictor?focused=1", "reason": "Full ML probability, BPM forecast, and feature importance."},
        ]
    return _default_navigation()


def _action_tag(risk: float, fit: float, success: float) -> str:
    """Return a GM action recommendation based on scores."""
    if risk < 35 and fit >= 60 and success >= 70:
        return "Call this week — top priority"
    if risk < 50 and fit >= 50 and success >= 55:
        return "Worth a look — schedule film"
    if success >= 65 and risk < 60:
        return "Watch film first — verify role fit"
    if risk >= 60:
        return "Pass for now — risk too high"
    return "Depth option — keep monitoring"


def _risk_label(score: float) -> str:
    if score < 35: return f"Low ({score:.0f}/100)"
    if score < 55: return f"Moderate ({score:.0f}/100)"
    return f"High ({score:.0f}/100)"


def _fit_label(score: float) -> str:
    if score >= 65: return f"Strong System Fit ({score:.0f}/100)"
    if score >= 50: return f"Moderate Fit ({score:.0f}/100)"
    return f"System Mismatch ({score:.0f}/100)"


def _explain_player(r: pd.Series, players: pd.DataFrame, include_ml: bool = True) -> str:
    """Return a full human-readable player explanation with score context."""
    ml = ml_predict(players[players["player_name"] == r["player_name"]]) if include_ml else None

    # Role determination
    role_map = {"G":"guard","PG":"point guard","SG":"shooting guard","SF":"small forward",
                "W":"3-and-D wing","F":"frontcourt piece","WI":"3-and-D wing","PU":"primary ball handler","PF":"power forward","C":"rim-running big"}
    role = role_map.get(r.get("position",""), "rotation piece")

    # Projected BPM context
    bpm = ml["future_bpm_prediction"] if ml else r.get("predicted_bpm", 0)
    bpm_label = ("positive rotation contributor" if bpm >= 1.5 else
                 "depth/role player" if bpm >= 0 else "production risk at this level")

    # Conference jump context
    conf = r.get("conference", "")
    conf_note = ""
    if conf in ["Big Ten", "SEC", "Big 12", "ACC"]:
        conf_note = "Already playing at Illinois level — minimal conference translation risk."
    elif conf in ["CUSA", "Sun Belt", "MAC", "WAC", "Horizon", "CAA"]:
        conf_note = f"Coming from {conf} — Illinois-level physicality jump is a meaningful risk factor."

    # Concern
    concern = ""
    if r.get("turnover_rate", 0) > 18: concern = f"High turnover rate ({r['turnover_rate']:.1f}%) — risky as a primary initiator in Underwood's pace system."
    elif r.get("three_pt_pct", 0) < 0.32 and r.get("position","") in ["G","PG","WI","PU"]: concern = f"Below-threshold shooting ({r['three_pt_pct']:.1%}) — may not fit Illinois's perimeter spacing scheme."
    elif r.get("defensive_rating", 110) > 107: concern = f"Defensive rating ({r['defensive_rating']:.0f}) — confirm on film whether this is team context or a real liability."
    elif r.get("minutes", 0) < 200: concern = f"Small sample size ({r['minutes']:.0f} minutes) — need more games to trust the efficiency numbers."
    else: concern = "No dominant red flag statistically — film validation needed on defensive rotations and Illinois-level physicality."

    lines = [
        f"{r['player_name']} | {r.get('position','')} | {r.get('school','')} ({r.get('conference','')})",
        f"Class: {r.get('class', r.get('year', '?'))} | {r.get('height','?')} | {r.get('ppg',0):.1f} PPG / {r.get('rpg',0):.1f} RPG / {r.get('apg',0):.1f} APG\n",
        f"Transfer Translation Score: {r.get('transfer_success_score',0):.0f}/100",
        f"  → estimates how likely this player's current production translates to an Illinois rotation role",
        f"Illinois Fit Score: {_fit_label(r.get('illinois_fit_score',50))}",
        f"  → how well his profile matches Underwood's system (3PT threshold, switching defense, playmaking)",
        f"Risk Score: {_risk_label(r.get('risk_score',50))} (lower = safer)",
        f"  → penalizes small sample, turnovers, poor efficiency, extreme usage mismatch",
    ]
    if ml:
        lines += [
            f"Projected BPM at Illinois: {bpm:+.1f} (estimates as a {bpm_label})",
            f"  → from RF+XGB+MLP ensemble; directional estimate on synthetic training data",
        ]
    if conf_note: lines.append(f"Conference context: {conf_note}")
    lines.append(f"Key concern: {concern}")
    lines.append(f"Illinois role: {role} in Underwood's system")
    lines.append(f"What Illinois should do: {_action_tag(r.get('risk_score',50), r.get('illinois_fit_score',50), r.get('transfer_success_score',50))}")
    return "\n".join(lines)


def _rule_based_chat(prompt: str, players: pd.DataFrame, roster: pd.DataFrame) -> ChatResult:
    q = prompt.lower()

    greetings = {"hi", "hello", "hey", "yo", "what's up", "whats up", "good morning", "good afternoon", "good evening"}
    gratitude = {"thanks", "thank you", "appreciate it", "thx"}

    if q.strip() in greetings or any(q.strip().startswith(g) for g in ["hi ", "hello ", "hey "]):
        return ChatResult(
            answer=(
                "Hey — what are you working on?\n\n"
                "You can ask me anything about Illinois basketball. Some things I'm good at:\n\n"
                "  • 'What are Illinois's biggest roster needs?' — real analysis using the actual roster\n"
                "  • 'Find me a 3-and-D wing' — specific players, full stats, explained in plain English\n"
                "  • 'Build a pretend roster with Cooper Flagg and Johni Broome' — projected PPG, rebounds, wins\n"
                "  • 'Scout Cooper Flagg' — full scouting report with recruiting recommendation\n"
                "  • 'Who are the hidden gems?' — undervalued targets before the market catches up\n\n"
                "Just ask naturally — I'll figure out what you need."
            ),
            evidence=[],
            navigation=[],
        )

    if q.strip() in gratitude:
        return ChatResult(
            answer="Anytime. What's next?",
            evidence=[],
            navigation=[],
        )

    # ── Glossary / metric explanation questions ───────────────────────────────
    _glossary_triggers = {
        "what does risk mean": "risk score",
        "what is risk score": "risk score",
        "explain risk": "risk score",
        "what does bpm mean": "bpm",
        "what is bpm": "bpm",
        "what does bpm forecast mean": "projected bpm",
        "what is projected bpm": "projected bpm",
        "what is the transfer translation score": "transfer translation score",
        "what is transfer translation score": "transfer translation score",
        "what does transfer translation mean": "transfer translation score",
        "what does the transfer translation score mean": "transfer translation score",
        "what is illinois fit score": "illinois fit score",
        "what does fit score mean": "illinois fit score",
        "what is hidden gem score": "hidden gem score",
        "what is the hidden gem score": "hidden gem score",
        "what does hidden gem score mean": "hidden gem score",
        "what is a hidden gem": "hidden gem score",
        "explain hidden gem": "hidden gem score",
        "what is value gap": "value gap score",
        "what is market inefficiency": "value gap score",
        "what is rotation impact": "rotation impact score",
        "what is ts%": "ts%",
        "what is true shooting": "ts%",
        "what is usage rate": "usage rate",
        "what does usage mean": "usage rate",
        "what is ast to": "ast/to",
        "what is dataset rank": "dataset rank",
        "what is public rank": "dataset rank",
        "what does public rank mean": "dataset rank",
        "explain the scores": None,
        "what do the scores mean": None,
        "explain all scores": None,
        "glossary": None,
        "metric definitions": None,
        "what are all the scores": None,
    }
    for trigger, key in _glossary_triggers.items():
        if trigger in q:
            if key and key in GLOSSARY:
                return ChatResult(
                    answer=GLOSSARY[key],
                    evidence=[],
                    navigation=[{"label": "Glossary", "path": "/glossary?focused=1", "reason": "Full metric glossary."}],
                )
            else:
                # Return a summary of all scores
                summary = "Score definitions for this product:\n\n"
                for k, v in list(GLOSSARY.items())[:6]:
                    summary += f"{k.title()}\n  {v[:120]}...\n\n"
                summary += "Open the Glossary page for full definitions of every metric."
                return ChatResult(
                    answer=summary,
                    evidence=[],
                    navigation=[{"label": "Glossary", "path": "/glossary?focused=1", "reason": "Full metric definitions."}],
                )

    # ── Data transparency questions ────────────────────────────────────────────
    if any(t in q for t in ["real player", "are these players", "are the players real", "fake player", "synthetic"]):
        return ChatResult(
            answer=DATA_TRANSPARENCY["are these real players"],
            evidence=[],
            navigation=[{"label": "Methodology", "path": "/methodology?focused=1", "reason": "Full data and model documentation."}],
        )

    if any(t in q for t in ["where does the data", "data come from", "data source", "what data", "where is the data"]):
        return ChatResult(
            answer=DATA_TRANSPARENCY["data source"],
            evidence=[],
            navigation=[{"label": "Methodology", "path": "/methodology?focused=1", "reason": "Full data sourcing explanation."}],
        )

    if any(t in q for t in ["only 50 players", "only 150", "why so few", "how many players", "dataset size", "why are there only"]):
        return ChatResult(
            answer=DATA_TRANSPARENCY["player count"],
            evidence=[],
            navigation=[{"label": "Methodology", "path": "/methodology?focused=1", "reason": "Dataset scope and limitations."}],
        )

    if any(t in q for t in ["is the model real", "is the ml real", "are models real", "trained on real", "real data or fake", "real or synthetic"]):
        return ChatResult(
            answer=DATA_TRANSPARENCY["model real"],
            evidence=[],
            navigation=[{"label": "Transfer Success Predictor", "path": "/transfer-success-predictor?focused=1", "reason": "Full model diagnostics."}],
        )

    if "current roster" in q or "illinois roster" in q or "who is on the team" in q or "our roster" in q:
        if not roster.empty:
            lines = ["2026-27 Illinois Roster:\n"]
            for r in roster.itertuples():
                raw_jersey = str(r.jersey) if hasattr(r, "jersey") else ""
                jersey = f"#{int(float(raw_jersey))}" if raw_jersey not in ("nan", "", "None") else " "
                lines.append(f"{jersey:5s} {r.player_name} | {r.position} | {r.class_year}")
            return ChatResult(
                answer="\n".join(lines),
                evidence=roster.to_dict("records"),
                navigation=[
                    {"label": "Roster Builder", "path": "/roster-builder?focused=1", "reason": "Explore depth chart and team construction."},
                ],
            )

    if "best shooter" in q or ("shoot" in q and "target" in q):
        board = players.sort_values(["three_pt_pct", "market_inefficiency_score"], ascending=False).head(5)
        lines = ["Top shooters on the current portal board:\n"]
        for r in board.itertuples():
            lines.append(f"  {r.player_name} ({r.school}) — {r.three_pt_pct:.1%} 3PT, Illinois fit {r.illinois_fit_score:.1f}, ML success {r.transfer_success_score:.1f}%")
        lines.append("\nPrioritize movement shooters who fit Illinois's off-ball spacing scheme. Run film on shot selection in early clock situations.")
        return ChatResult(
            answer="\n".join(lines),
            evidence=board[["player_name", "three_pt_pct", "illinois_fit_score", "market_inefficiency_score"]].to_dict("records"),
            navigation=_navigation_for_query(q),
        )

    if "wing defender" in q or "find wing" in q or "3 and d" in q or "3-and-d" in q:
        board = players[players["position"].isin(["WI"])].sort_values(
            ["steal_rate", "defensive_rating", "three_pt_pct"],
            ascending=[False, True, False],
        ).head(4)
        if board.empty:
            board = players.sort_values("illinois_fit_score", ascending=False).head(4)
        lines = [
            "3-and-D wing options for Illinois:\n",
            "Illinois needs wings who can: (1) defend multiple positions without giving up easy buckets, "
            "(2) shoot 36.5%+ from three so defenders can't sag off them, (3) move without the ball.\n"
        ]
        for _, r in board.iterrows():
            # Explain each player fully
            shoot_grade = "Elite shooter" if r["three_pt_pct"] >= 0.40 else "Good shooter" if r["three_pt_pct"] >= 0.365 else "Below Illinois's shooting threshold"
            def_grade = "Excellent defender" if r["defensive_rating"] <= 96 else "Solid defender" if r["defensive_rating"] <= 102 else "Average defense"
            fit = "Strong fit" if r["illinois_fit_score"] >= 60 else "Moderate fit" if r["illinois_fit_score"] >= 48 else "Needs evaluation"
            action = _action_tag(r["risk_score"], r["illinois_fit_score"], r["transfer_success_score"])
            lines.append(
                f"{r['player_name']} | {r['school']} ({r['conference']})\n"
                f"  Shooting: {r['three_pt_pct']:.1%} from 3 — {shoot_grade} for Illinois's spacing scheme\n"
                f"  Defense: {r['defensive_rating']:.0f} defensive rating — {def_grade} "
                f"(under 100 = elite; opponents score under a point per possession when he's on the floor)\n"
                f"  Steals: {r['steal_rate']:.1f}% steal rate — {'above average ball-hawk' if r['steal_rate'] > 2.0 else 'normal range'} "
                f"(creates turnovers that turn into transition buckets)\n"
                f"  Illinois fit: {r['illinois_fit_score']:.0f}/100 — {fit}\n"
                f"  What to do: {action}\n"
            )
        lines.append(
            "How to use this: verify switchability on film — can he guard a point guard on one possession "
            "and a power forward on the next without getting beaten? That's Underwood's switching scheme in one sentence."
        )
        return ChatResult(
            answer="\n".join(lines),
            evidence=board[["player_name", "school", "steal_rate", "block_rate", "defensive_rating", "three_pt_pct", "illinois_fit_score"]].to_dict("records"),
            navigation=_navigation_for_query(q),
        )

    if "undervalued" in q or "hidden gem" in q:
        board = players.sort_values(["market_inefficiency_score", "projected_impact_score"], ascending=False).head(3)
        lines = [
            "Hidden gem targets — players our model scores above their dataset rank:\n",
            "(Hidden Gem Score: 0-100 — higher = stronger production relative to dataset/market rank)",
            "(Dataset Rank: prototype field, NOT from ESPN/Rivals/On3)\n",
        ]
        for _, r in board.iterrows():
            lines.append(_explain_player(r, players))
            lines.append("")
        lines.append("These gaps compress fast — initiate contact before competing programs identify the same inefficiency.")
        return ChatResult(
            answer="\n".join(lines),
            evidence=board[["player_name", "hidden_gem_score", "market_inefficiency_score", "public_transfer_rank"]].to_dict("records"),
            navigation=_navigation_for_query(q),
        )

    if "compare" in q:
        names = [n.strip() for n in prompt.replace("Compare", "").replace("compare", "").split("and") if n.strip()]
        if len(names) >= 2:
            a = players[players["player_name"].str.lower() == names[0].lower()]
            b = players[players["player_name"].str.lower() == names[1].lower()]
            if not a.empty and not b.empty:
                p1, p2 = a.iloc[0], b.iloc[0]
                winner = p1 if p1["illinois_fit_score"] >= p2["illinois_fit_score"] else p2
                loser = p2 if winner["player_name"] == p1["player_name"] else p1
                answer = (
                    f"{winner['player_name']} is the stronger Illinois fit.\n\n"
                    f"{winner['player_name']}: {winner['illinois_fit_score']:.1f} fit, {winner['transfer_success_score']:.1f}% ML success, {winner['risk_score']:.1f} risk\n"
                    f"{loser['player_name']}: {loser['illinois_fit_score']:.1f} fit, {loser['transfer_success_score']:.1f}% ML success, {loser['risk_score']:.1f} risk\n\n"
                    f"Keep {loser['player_name']} as a backup if NIL or role discussions stall with {winner['player_name']}."
                )
                return ChatResult(
                    answer=answer,
                    evidence=[p1.to_dict(), p2.to_dict()],
                    navigation=[{"label": "Compare Players", "path": "/compare-players?focused=1", "reason": "Run full radar comparison."}],
                )

    if "scouting report" in q:
        maybe_name = prompt.split("for")[-1].strip()
        match = players[players["player_name"].str.lower() == maybe_name.lower()]
        if match.empty and maybe_name:
            match = players[players["player_name"].str.lower().str.contains(maybe_name.lower(), na=False)]
        if match.empty:
            match = players.sort_values("illinois_fit_score", ascending=False).head(1)
        p = match.iloc[0]
        answer = (
            f"{p['player_name']} — {p['archetype']} | {p.get('school', '')} | {p['position']}\n\n"
            f"ML Profile:\n"
            f"  Success probability: {p['transfer_success_score']:.1f}%\n"
            f"  Illinois fit: {p['illinois_fit_score']:.1f}/100\n"
            f"  Risk score: {p['risk_score']:.1f}/100\n\n"
            f"Key stats: {p['three_pt_pct']:.1%} 3PT, {p.get('ts_pct', 0):.1%} TS, {p.get('assist_rate', 0):.1f}% AST, {p.get('defensive_rating', 0):.0f} Drtg\n\n"
            f"Use the Scouting Center below for the full report with PDF export."
        )
        return ChatResult(
            answer=answer,
            evidence=[p.to_dict()],
            navigation=[{"label": "Scouting Center", "path": "/scouting-center?focused=1", "reason": "Full scouting report with PDF export."}],
        )

    # Off-topic / non-basketball / nonsense → redirect gracefully
    # Only redirect clear non-basketball topics; be permissive for anything staff might ask
    # Clearly non-basketball topics: weather, celebrities not in college basketball, etc.
    _clearly_offtopic = any(w in q for w in [
        "weather", "temperature", "forecast", "lebron", "nba", "nfl", "soccer",
        "politics", "stock", "recipe", "movie", "music", "game of thrones",
    ])
    basketball_words = {
        "illinois", "player", "transfer", "portal", "guard", "wing", "big", "center",
        "forward", "recruit", "scout", "roster", "fit", "risk", "gem", "bpm", "shooting",
        "defense", "rebound", "turnover", "assist", "conference", "big ten", "basketball",
        "we", "our", "us", "target", "add", "get", "build", "need", "team", "coach",
        "gm", "recommendation", "priority", "who", "find", "show", "best", "top",
        "what", "which", "how", "give",
    }
    # Only redirect if clearly off-topic AND no basketball words as full words
    q_words = set(q.split())
    if _clearly_offtopic or not any(word in q_words for word in basketball_words):
        return ChatResult(
            answer=(
                "I'm focused on Illinois basketball operations — I can't help with that.\n\n"
                "Here's what I can do:\n"
                "- 'Find me the best transfer guards for Illinois'\n"
                "- 'Who are the top hidden gems in the portal?'\n"
                "- 'Generate a scouting report for Ivan White'\n"
                "- 'What are Illinois's biggest roster needs?'\n"
                "- 'Compare the top two portal wings'"
            ),
            evidence=[],
            navigation=_default_navigation(),
        )

    # Final GM recommendation
    if "final" in q and ("recommendation" in q or "gm" in q or "verdict" in q):
        top = players.sort_values("illinois_fit_score", ascending=False).head(3)
        best = top.iloc[0]
        ml = ml_predict(players[players["player_name"] == best["player_name"]])
        ml_str = f"{ml['transfer_success_probability']:.1f}% success probability, {ml['future_bpm_prediction']:+.2f} BPM forecast" if ml else f"fit score {best['illinois_fit_score']:.1f}"
        lines = [
            f"GM Recommendation — current board:\n",
            f"Priority target: {best['player_name']} ({best['position']}, {best['school']})",
            f"  ML assessment: {ml_str}",
            f"  Illinois fit: {best['illinois_fit_score']:.1f}/100 | Risk: {best['risk_score']:.1f}/100\n",
            "Full board top 3:",
        ]
        for _, r in top.iterrows():
            lines.append(f"  {r['player_name']} ({r['position']}, {r['school']}) — fit {r['illinois_fit_score']:.1f}, ML success {r['transfer_success_score']:.1f}%")
        lines.append("\nNext step: Run film on Tier 1 targets, confirm role acceptance, and initiate first-contact by end of week.")
        return ChatResult(
            answer="\n".join(lines),
            evidence=top.to_dict("records"),
            navigation=[
                {"label": "Recruiting Center", "path": "/recruiting-center?focused=1", "reason": "Full GM priority board."},
                {"label": "Player Intelligence", "path": "/player-intelligence?focused=1", "reason": "Deep dive on each target."},
            ],
        )

    # ── Deep roster needs analysis using REAL Illinois roster data ──────────────
    _roster_needs_triggers = [
        "roster need", "biggest need", "what does illinois need", "what do we need",
        "who should we get", "what type of player", "who should illinois get",
        "what position", "what are our needs", "roster gap", "what illinois needs",
        "what should illinois prioritize", "biggest weakness", "what do they need",
    ]
    if any(t in q for t in _roster_needs_triggers):
        ctx = ILLINOIS_CONTEXT
        # Analyze the REAL roster data
        avg_3pt = roster["three_pt_pct"].mean() if not roster.empty else 0.33
        avg_drtg = roster["defensive_rating"].mean() if not roster.empty else 102
        avg_ast = roster["assist_rate"].mean() if not roster.empty else 12
        below_threshold = roster[roster["three_pt_pct"] < 0.365] if not roster.empty else pd.DataFrame()

        # Count available portal players for each need
        shooters_avail = players[players["three_pt_pct"] >= ctx["fit_profile"]["3pt_threshold"]]
        wings_avail = players[players["position"].isin(["WI"])]
        bigs_avail = players[players["position"].isin(["PF", "C"]) & (players["three_pt_pct"] >= 0.33)]

        # Best available for each need
        best_shooter = shooters_avail.sort_values("illinois_fit_score", ascending=False).head(1).iloc[0] if not shooters_avail.empty else None
        best_wing = wings_avail.sort_values("illinois_fit_score", ascending=False).head(1).iloc[0] if not wings_avail.empty else None
        best_big = bigs_avail.sort_values("illinois_fit_score", ascending=False).head(1).iloc[0] if not bigs_avail.empty else None

        lines = [
            "Illinois's biggest roster needs going into this portal cycle — based on real 2024-25 roster data:\n",
        ]

        lines.append("\n1. Illinois needs a reliable 3-point shooter")
        lines.append(
            f"Why: Illinois's current roster averages {avg_3pt:.1%} from three as a team. "
            f"Underwood's offense requires 36.5%+ from three for the spacing to work — "
            f"when shooters are below that, defenders stop respecting the shot and pack the paint, "
            f"shutting down driving lanes and the pick-and-roll system entirely."
        )
        if not roster.empty:
            lines.append(f"\nLooking at the returning players:")
            for _, p in roster.iterrows():
                pct = p["three_pt_pct"]
                flag = "✓ above threshold" if pct >= 0.365 else "✗ below threshold"
                lines.append(f"  {p['player_name']} ({p.get('position','?')}): {pct:.1%} 3PT — {flag}")
        lines.append(
            f"\nAll {len(below_threshold)} returning shooters are below the 36.5% threshold. "
            f"Illinois needs at least one high-volume perimeter shooter who can force defenders to stay attached. "
            f"There are {len(shooters_avail)} portal players currently available who meet this threshold."
        )
        if best_shooter is not None:
            lines.append(f"\nBest available shooter: {best_shooter['player_name']} ({best_shooter['school']}) — {best_shooter['three_pt_pct']:.1%} from 3, Illinois fit {best_shooter['illinois_fit_score']:.0f}/100")

        lines.append("\n2. Illinois needs a 3-and-D wing")
        lines.append(
            "Why: Underwood's switching defense requires perimeter players who can guard a point guard "
            "on one possession and a power forward on the next — without giving up a mismatch. "
            "Illinois's current wing depth lacks a proven perimeter stopper who also hits enough threes "
            "to keep defenders honest. Without this, the switching scheme has exploitable holes."
        )
        lines.append(
            f"\nThere are {len(wings_avail)} wing players (BartTorvik 'WI' classification) currently in the portal dataset. "
            "Look for: steal rate above 2%, defensive rating under 100, and 3PT% above 36%."
        )
        if best_wing is not None:
            lines.append(f"\nBest available wing: {best_wing['player_name']} ({best_wing['school']}) — "
                        f"{best_wing['three_pt_pct']:.1%} 3PT, {best_wing['defensive_rating']:.0f} defensive rating, "
                        f"Illinois fit {best_wing['illinois_fit_score']:.0f}/100")

        lines.append("\n3. Illinois needs frontcourt depth — specifically a stretch big")
        lines.append(
            "Why: Tomislav Ivisic is a senior (leaving after this year). "
            "Losing him creates a frontcourt hole — Illinois will need at least one power forward "
            "or center who can defend the rim AND stretch the floor (shoot mid-range and beyond). "
            "A pure post-up center who can't step out to 3 doesn't fit Underwood's spacing system."
        )
        lines.append(
            f"\nThere are {len(bigs_avail)} stretch bigs (PF/C with 33%+ 3PT) available in the portal."
        )
        if best_big is not None:
            lines.append(f"\nBest available stretch big: {best_big['player_name']} ({best_big['school']}) — "
                        f"{best_big['three_pt_pct']:.1%} 3PT, Illinois fit {best_big['illinois_fit_score']:.0f}/100")

        lines.append(
            "\n\nOpen the Recruiting Center to see tiered boards for each of these needs specifically. "
            "Each board is filtered and ranked for Illinois's system — you can go straight to wing defenders, "
            "stretch bigs, or perimeter shooters."
        )

        return ChatResult(
            answer="\n".join(lines),
            evidence=[p.to_dict() for p in [best_shooter, best_wing, best_big] if p is not None],
            navigation=[
                {"label": "Recruiting Center", "path": "/recruiting-center?focused=1", "reason": "Full role-based boards for each need."},
                {"label": "Roster Builder", "path": "/roster-builder?focused=1", "reason": "Build your hypothetical roster additions."},
            ],
        )

    # ── Generic fallback — show top insights ─────────────────────────────────
    top_player = players.sort_values("illinois_fit_score", ascending=False).iloc[0]
    lines = [
        "Here's a quick read on the current board:\n",
        f"Top Illinois fit: {top_player['player_name']} ({top_player['position']}, {top_player['school']}) — "
        f"{top_player['three_pt_pct']:.1%} 3PT, {top_player['ppg']:.1f} PPG",
        "",
        "Ask something specific and I'll give you a real answer. For example:",
        "  • 'What are Illinois's biggest roster needs?' — full analysis with real roster data",
        "  • 'Find me a 3-and-D wing' — specific players with full explanations",
        "  • 'Scout Cooper Flagg' — detailed scouting report",
        "  • 'Build a hypothetical roster with Flagg and Broome' — projected team stats",
    ]
    return ChatResult(
        answer="\n".join(lines),
        evidence=[],
        navigation=[
            {"label": "Recruiting Center", "path": "/recruiting-center?focused=1", "reason": "See all available portal targets."},
        ],
    )


_AGENT_DISPLAY_NAMES: dict[str, str] = {
    "recruiting":          "Recruiting Agent",
    "transfer-portal":     "Transfer Portal Agent",
    "hidden-gem":          "Hidden Gem Agent",
    "scouting":            "Scouting Agent",
    "roster-builder":      "Roster Builder Agent",
    "compare":             "Compare Players Agent",
    "risk-fit":            "Risk & Fit Agent",
    "player-development":  "Player Development Agent",
    "market-inefficiency": "Market Inefficiency Agent",
    "scenario":            "Scenario Agent",
    "game-plan":           "Game Plan Agent",
}

_AGENT_ROUTES: dict[str, str] = {
    "recruiting":          "/recruiting-center",
    "transfer-portal":     "/transfer-success-predictor",
    "hidden-gem":          "/hidden-gem-lab",
    "scouting":            "/scouting-center",
    "roster-builder":      "/roster-builder",
    "compare":             "/compare-players",
    "risk-fit":            "/player-intelligence",
    "player-development":  "/player-intelligence",
    "market-inefficiency": "/hidden-gem-lab",
    "scenario":            "/roster-builder",
    "game-plan":           "/scouting-center",
}

_INTENT_MAP: list[tuple[str, list[str]]] = [
    # Compare two players — must come first so "compare" doesn't get caught by other agents
    ("compare",            ["compare", "versus", " vs ", "who is better", "which player is", "head to head", "head-to-head"]),

    # Scouting — specific player breakdown
    ("scouting",           ["scouting report", "scout ", "breakdown of", "profile for", "generate a report", "full report on", "tell me about"]),

    # Game plan — opponent prep
    ("game-plan",          ["game plan", "defend against", "opponent prep", "matchup", "how to stop"]),

    # Transfer portal — learning about the portal, player movement
    ("transfer-portal",    [
        "transfer portal", "portal target", "portal move", "ml rank",
        "transferring", "learn about transfer", "how does the portal", "what is the portal",
        "transfer window", "portal entry", "enter the portal", "in the portal",
        "transfer season", "portal players", "portal cycle",
        "top transfers", "best transfers", "ml ranked", "success probability",
    ]),

    # Roster needs and construction — BEFORE recruiting so "what do we need" goes here
    ("roster-builder",     [
        "build my roster", "build a roster", "depth chart", "scholarship", "rotation plan",
        "pretend roster", "build roster", "roster builder", "create a roster", "make a roster",
        "build a team", "pretend team", "predict analytics", "build around", "hypothetical roster",
        "roster simulation", "add players", "test a roster", "what would happen if",
        "combine players", "player combination",
        # Any "roster" mention — the most natural thing a GM says
        "roster help", "help with roster", "help me with roster", "need roster",
        "roster advice", "about the roster", "roster question", "roster work",
        "work on the roster", "roster planning", "roster construction",
        "i need roster", "roster support", "roster analysis",
        # Roster needs analysis
        "roster need", "biggest need", "what do we need", "what does illinois need",
        "roster gap", "our weakness", "biggest weakness", "roster weakness",
        "what should we add", "what position do we need", "what role do we need",
        "fill the gap", "strengthen the roster", "improve the roster",
    ]),

    # Hidden gems and market value
    ("hidden-gem",         [
        "hidden gem", "under the radar", "sleeping on", "overlooked", "undervalued player",
        "undervalued target", "best value", "value targets", "market value",
        "show me undervalued", "find undervalued", "who is undervalued",
        "market is sleeping", "move before",
    ]),

    # Market inefficiency specifically
    ("market-inefficiency",["market inefficiency", "overranked", "overrated by public", "mispriced", "public rank is wrong"]),

    # Risk and fit analysis
    ("risk-fit",           [
        "risk score", "red flag", "safe floor", "risky target", "high risk", "low risk target",
        "fit score breakdown", "safest target", "who is risky", "risky players",
        "avoid risk", "who should we avoid", "stay away from",
        "highest fit", "best fit", "best illinois fit", "illinois fit",
    ]),

    # Player development ceiling
    ("player-development", ["develop ", "development plan", "improve their", "work on ", "upside on", "ceiling of", "develop a player", "most upside", "highest upside", "highest ceiling"]),

    # Scenario / what-if
    ("scenario",           ["what if we add", "simulate adding", "hypothetical roster", "what if illinois"]),

    # Recruiting — finding specific player types (catches position queries)
    ("recruiting",         [
        "recruit", "who should illinois get", "find me a", "find a transfer", "recruiting board",
        "find a wing", "find wing", "wing defender", "3 and d", "3-and-d",
        "find a guard", "find guards", "find me a guard", "best guards",
        "find a big", "rim protector", "stretch big", "find me a big", "best bigs",
        "shooting guard", "playmaking guard", "ball handler",
        "who should we get", "who should we recruit", "who should illinois recruit",
        "who should we add", "who should illinois add", "who should we target",
        "best available", "best shooter", "top shooters",
        "best player available", "top available",
    ]),
]

_ROUTING_NOTES: dict[str, str] = {
    "transfer-portal": "Note: College basketball uses the Transfer Portal, not trades. Routing to the Transfer Portal Agent.",
}

_AGENT_SYSTEM_HINTS: dict[str, str] = {
    "recruiting":          "Focus on Illinois recruiting boards, fit scores, role needs, and target prioritization. Be specific about which players match Underwood's system.",
    "transfer-portal":     "Focus on transfer success probability, conference translation, risk/reward, and ML predictions. Always cite the specific probability and BPM forecast.",
    "scenario":            "Focus on roster construction tradeoffs, scholarship counts, depth chart impacts, and team identity shifts.",
    "hidden-gem":          "Focus on market inefficiency, undervalued players, small-school translation, and hidden gem scores. Explain WHY the model values them differently than public consensus.",
    "roster-builder":      "Focus on building complete roster plans, scholarship allocation, rotation balance, and positional depth gaps.",
    "scouting":            "Focus on strengths, weaknesses, shot profiles, defensive tendencies, and game-plan-ready recommendations. Always include the ML success probability.",
    "player-development":  "Focus on individual development priorities, improvement paths, and ML-forecasted BPM ceilings. Be specific about what to develop.",
    "compare":             "Focus on direct player comparisons: stats, fit, risk, upside, and a clear Illinois-fit recommendation. One player should win the comparison.",
    "risk-fit":            "Focus on risk score breakdowns, red flags, role mismatches, and confidence-weighted fit assessments. Flag specific statistical concerns.",
    "market-inefficiency": "Focus on undervalued targets, production vs visibility gaps, and value-based targeting strategies. Show actual rank gaps.",
    "game-plan":           "Focus on opponent scouting, player threats, defensive schemes, and offensive attack recommendations.",
    "main":                "You are a central basketball operations assistant. Route queries to the right specialist and give direct, specific answers backed by data.",
}


def _detect_intent(query: str) -> str | None:
    q = query.lower()

    # Keyword phrase matching (ordered — first match wins)
    for agent_id, keywords in _INTENT_MAP:
        if any(kw in q for kw in keywords):
            return agent_id

    # Word-level fallback — single words that unambiguously signal an agent
    words = set(q.replace(":", "").replace("?", "").replace("!", "").split())
    if "roster" in words:
        return "roster-builder"
    if "scouting" in words or "scout" in words:
        return "scouting"
    if "compare" in words:
        return "compare"

    return None


def _routed_result(routed_agent_id: str, inner: ChatResult, query: str) -> ChatResult:
    name = _AGENT_DISPLAY_NAMES.get(routed_agent_id, routed_agent_id)
    route = _AGENT_ROUTES.get(routed_agent_id, "/")
    note = _ROUTING_NOTES.get(routed_agent_id, "")
    note_line = f"\n{note}" if note else ""
    # AGENT_SWITCH: prefix lets the frontend parse and switch the active agent chip
    header = f"AGENT_SWITCH:{routed_agent_id}\nSwitching you to the {name}.{note_line}\n\n"
    # Only ONE navigation button — the relevant tool for this agent
    nav = [{"label": f"Open {name}", "path": f"{route}?focused=1", "reason": f"Open the {name} dashboard."}]
    return ChatResult(answer=header + inner.answer, evidence=inner.evidence, navigation=nav)


def _agent_specific_response(agent_id: str, prompt: str, players: pd.DataFrame, roster: pd.DataFrame) -> ChatResult | None:
    q = prompt.lower()

    # ── Meta-questions: explain what the agent does ───────────────────────────
    if _is_meta_question(q):
        desc = AGENT_DESCRIPTIONS.get(agent_id, AGENT_DESCRIPTIONS["main"])
        base_route = _AGENT_ROUTES.get(agent_id, "/")
        # Home ("/") doesn't use focused mode — it IS the agents page
        focused_path = f"{base_route}?focused=1" if base_route != "/" else "/"
        nav = [{"label": _AGENT_DISPLAY_NAMES.get(agent_id, "Dashboard"),
                "path": focused_path,
                "reason": "Open the interactive tool for this agent."}]
        return ChatResult(answer=desc, evidence=[], navigation=nav or _default_navigation())

    # ── Agent-specific intelligence ───────────────────────────────────────────

    if agent_id == "recruiting":
        ctx = ILLINOIS_CONTEXT
        fit = ctx["fit_profile"]

        # Detect position/role intent from query
        _guard_q = any(t in q for t in ["guard", "pg", "sg", "ball handler", "playmaker", "point guard", "shooting guard"])
        _wing_q  = any(t in q for t in ["wing", "forward", "sf", "3 and d", "3-and-d", "small forward"])
        _big_q   = any(t in q for t in ["big", "center", "pf", "power forward", "rim protect", "stretch big", "4", "5", "post"])

        base = players[players["risk_score"] <= fit["risk_max"]].copy()

        if _guard_q:
            base = base[base["position"].isin(["PG", "G", "PU"])].sort_values("assist_rate", ascending=False)
        elif _wing_q:
            base = base[base["position"].isin(["WI", "PF"])].sort_values(
                ["steal_rate", "block_rate", "three_pt_pct"], ascending=False)
        elif _big_q:
            base = base[base["position"].isin(["PF", "C"])].sort_values(
                ["block_rate", "def_rebound_rate"], ascending=False)
        else:
            base = base.sort_values(["illinois_fit_score", "transfer_success_score"], ascending=False)

        filtered = base[base["three_pt_pct"] >= fit["3pt_threshold"] - 0.025]
        if len(filtered) < 6:
            filtered = base

        board = filtered.head(6)

        def _tier_line(r: object) -> str:
            tags = []
            if r.assist_rate >= fit["assist_rate_min"]:
                tags.append("playmaker")
            if r.three_pt_pct >= fit["3pt_threshold"]:
                tags.append("shooter")
            if r.defensive_rating <= fit["def_rating_max"]:
                tags.append("defender")
            tag_str = f" [{', '.join(tags)}]" if tags else ""
            return (
                f"  {r.player_name} ({r.position}, {r.school}){tag_str}\n"
                f"    Fit {r.illinois_fit_score:.1f} | ML success {r.transfer_success_score:.1f}% | Risk {r.risk_score:.1f} | 3PT {r.three_pt_pct:.1%}"
            )

        t1, t2, t3 = board.head(2), board.iloc[2:4], board.iloc[4:6]
        lines = [
            "Here are the top transfer targets for Illinois right now:\n",
            "Call these players this week:",
        ] + [_tier_line(r) for r in t1.itertuples()] + [
            "\nStrong options worth a conversation:",
        ] + [_tier_line(r) for r in t2.itertuples()] + [
            "\nKeep an eye on these — call if the top targets fall through:",
        ] + [_tier_line(r) for r in t3.itertuples()] + [
            "\nWhat Illinois needs most this cycle:",
        ] + [f"  {need}" for need in ctx["known_needs_2026"]]

        return ChatResult(
            answer="\n".join(lines),
            evidence=board[["player_name", "position", "school", "illinois_fit_score", "transfer_success_score", "risk_score", "three_pt_pct"]].to_dict("records"),
            navigation=[
                {"label": "Recruiting Center", "path": "/recruiting-center?focused=1", "reason": "Full board with all filters."},
                {"label": "Player Intelligence", "path": "/player-intelligence?focused=1", "reason": "Deep-dive any Tier 1 target."},
            ],
        )

    if agent_id == "transfer-portal":
        board = players.sort_values("transfer_success_score", ascending=False).head(3)
        lines = [
            "Illinois Model-Scored Portal Targets — ranked by Transfer Translation Score:\n",
            "(Transfer Translation Score: 0-100 — estimates likelihood of Big Ten production translation)",
            "(Prototype model trained on synthetic data calibrated to NCAA distributions — directional, not definitive)\n",
        ]
        for _, r in board.iterrows():
            lines.append(_explain_player(r, players))
            lines.append("")
        lines.append(
            "Open the Transfer Success Predictor for per-player feature importance, "
            "per-model breakdown (RF vs XGB vs MLP), and full model diagnostics."
        )
        return ChatResult(
            answer="\n".join(lines),
            evidence=board[["player_name", "school", "transfer_success_score", "illinois_fit_score", "risk_score"]].to_dict("records"),
            navigation=[
                {"label": "Transfer Success Predictor", "path": "/transfer-success-predictor?focused=1", "reason": "Full model predictions per player."},
                {"label": "Compare Players", "path": "/compare-players?focused=1", "reason": "Head-to-head comparison."},
            ],
        )

    if agent_id == "hidden-gem":
        # Low-usage, high-efficiency filter
        if "low usage" in q or "low-usage" in q or ("high efficiency" in q or "efficient" in q and "low" in q):
            ts_median = float(players["ts_pct"].median())
            board = players[
                (players["usage_rate"] < 22) & (players["ts_pct"] > ts_median)
            ].sort_values(["market_inefficiency_score", "hidden_gem_score"], ascending=False).head(4)
            if board.empty:
                board = players.sort_values("hidden_gem_score", ascending=False).head(4)
            lines = [
                "Low-usage, high-efficiency targets:",
                "(Hidden Gem Score: 0-100 where higher = stronger production relative to dataset rank)\n",
            ]
            for _, r in board.iterrows():
                lines.append(_explain_player(r, players))
                lines.append("")
            lines.append("These players produce efficiently without dominating ball distribution — valuable role-fit additions for a deep rotation.")
            return ChatResult(
                answer="\n".join(lines),
                evidence=board[["player_name", "school", "ts_pct", "usage_rate", "hidden_gem_score"]].to_dict("records"),
                navigation=[
                    {"label": "Hidden Gem Lab", "path": "/hidden-gem-lab?focused=1", "reason": "Full undervalued player analysis."},
                    {"label": "Recruiting Center", "path": "/recruiting-center?focused=1", "reason": "Add to contact board."},
                ],
            )

        board = players.sort_values(["market_inefficiency_score", "projected_impact_score"], ascending=False).head(3)
        lines = [
            "Top hidden gems — players our scoring model values significantly above their dataset rank:\n",
            "(Hidden Gem Score: 0-100 — higher means stronger production relative to market attention)",
            "(Dataset Rank: prototype ranking field, NOT from ESPN/Rivals/On3 — used to model market inefficiency)\n",
        ]
        for _, r in board.iterrows():
            lines.append(_explain_player(r, players))
            lines.append("")
        lines.append(
            "These gaps close quickly once analytics data spreads to competing programs. "
            "Prioritize film on the top 1-2 before committing to initial contact."
        )
        return ChatResult(
            answer="\n".join(lines),
            evidence=board[["player_name", "school", "hidden_gem_score", "market_inefficiency_score", "public_transfer_rank"]].to_dict("records"),
            navigation=[
                {"label": "Hidden Gem Lab", "path": "/hidden-gem-lab?focused=1", "reason": "Full market inefficiency chart."},
                {"label": "Recruiting Center", "path": "/recruiting-center?focused=1", "reason": "Add hidden gems to contact priorities."},
            ],
        )

    if agent_id == "scouting":
        maybe_name = prompt.split("for")[-1].strip() if "for" in q else ""
        if not maybe_name and "scout " in q:
            maybe_name = q.split("scout ")[-1].strip().title()
        match = pd.DataFrame()
        player_not_found = False
        if maybe_name:
            match = players[players["player_name"].str.lower() == maybe_name.lower()]
            if match.empty:
                match = players[players["player_name"].str.lower().str.contains(maybe_name.lower(), na=False)]
            if match.empty:
                player_not_found = True
        if match.empty and not player_not_found:
            match = players.sort_values("illinois_fit_score", ascending=False).head(1)
        if player_not_found and match.empty:
            top_fit = players.sort_values("illinois_fit_score", ascending=False).head(3)
            lines = [f"'{maybe_name}' isn't in the prototype database (150 synthetic demo profiles).\n",
                     "Top available targets to scout (by Illinois Fit Score):"]
            for _, r in top_fit.iterrows():
                lines.append(f"  {r['player_name']} ({r['position']}, {r['school']}) — Fit {r['illinois_fit_score']:.0f}/100, Translation {r['transfer_success_score']:.0f}/100")
            lines.append("\nOpen the Scouting Center to generate a full report with PDF export.")
            return ChatResult(
                answer="\n".join(lines),
                evidence=top_fit.to_dict("records"),
                navigation=[{"label": "Scouting Center", "path": "/scouting-center?focused=1", "reason": "Generate a scouting report."}],
            )

        p = match.iloc[0]
        lines = [f"SCOUTING REPORT\n", _explain_player(p, players), ""]

        comps = compute_similarity(players, p["player_name"], top_n=2)
        if not comps.empty:
            lines.append(f"Comparable profiles in dataset: {', '.join(comps['player_name'].tolist())}")
        lines.append("\nOpen Scouting Center for the full structured report with PDF export.")
        return ChatResult(
            answer="\n".join(lines),
            evidence=[p.to_dict()],
            navigation=[
                {"label": "Scouting Center", "path": "/scouting-center?focused=1", "reason": "Full report with PDF export."},
                {"label": "Transfer Success Predictor", "path": "/transfer-success-predictor?focused=1", "reason": "Full ML prediction for this player."},
            ],
        )

    if agent_id == "roster-builder":
        ctx = ILLINOIS_CONTEXT

        # ── Conversational "build me a roster" request ─────────────────────────
        _build_triggers = [
            "pretend roster", "build roster", "build a roster", "build my roster",
            "hypothetical", "predict analytics", "test a roster", "what would happen",
            "combine players", "build around", "make a team", "create a roster",
        ]
        if any(t in q for t in _build_triggers):
            top5 = players.sort_values("illinois_fit_score", ascending=False).head(5)
            outcomes = roster_outcomes(top5)
            lines = [
                "Let's build it. Here's how it works:\n",
                "You pick the players — I'll calculate projected points per game, rebounds, assists, "
                "offensive efficiency, defensive efficiency, and estimated wins for that exact lineup, "
                "with a plain-English explanation of every number.\n",
                "To get started: open the Roster Builder below, search for any players you want, "
                "and click to add them. The stats update live as you add or remove players.\n",
                "Here's a preview with the top 5 Illinois-fit players to show you what the output looks like:\n",
                f"If Illinois adds: {', '.join(top5['player_name'].tolist())}\n",
                f"  → Projected scoring: ~{outcomes.get('projected_ppg',0):.1f} PPG",
                f"  → Rebounds: ~{outcomes.get('projected_rpg',0):.1f} RPG",
                f"  → Assists: ~{outcomes.get('projected_apg',0):.1f} APG",
                f"  → Offensive efficiency: {outcomes.get('team_ortg',0):.1f} (points per 100 possessions)",
                f"  → Defensive efficiency: {outcomes.get('team_drtg',0):.1f} (lower = better defense)",
                f"  → Net rating: {outcomes.get('net_rating',0):+.1f} → projected ~{outcomes.get('projected_wins',20):.0f}-win season",
                f"  → Team style: {outcomes.get('team_identity','')}",
                "\nThe Roster Builder lets you swap any player in or out and see those numbers change instantly. "
                "Want me to suggest players for a specific need — like a 3-and-D wing or a stretch big?",
            ]
            return ChatResult(
                answer="\n".join(lines),
                evidence=top5.to_dict("records"),
                navigation=[
                    {"label": "Roster Builder", "path": "/roster-builder?focused=1", "reason": "Build your hypothetical roster and see full projected stats."},
                ],
            )

        shooters = players[players["three_pt_pct"] >= ctx["fit_profile"]["3pt_threshold"]]
        playmakers = players[players["assist_rate"] >= ctx["fit_profile"]["assist_rate_min"]]
        defenders = players[players["defensive_rating"] <= ctx["fit_profile"]["def_rating_max"]]
        stretch_bigs = players[players["position"].isin(["PF", "WI"]) & (players["three_pt_pct"] >= 0.33)]

        best_adds = players.sort_values(["illinois_fit_score", "transfer_success_score"], ascending=False).head(4)
        outcomes = roster_outcomes(best_adds)

        lines = [
            f"Illinois roster breakdown — here's where things stand:\n",
            "What Illinois needs most right now:",
        ] + [f"  • {need}" for need in ctx["known_needs_2026"]] + [
            f"\nWhat's available in the portal right now:",
            f"  • Shooters hitting 36.5%+ from 3: {len(shooters)} players available",
            f"  • Playmaking guards (16%+ assist rate): {len(playmakers)} players available",
            f"  • Defenders (under 100.5 defensive rating): {len(defenders)} players available",
            f"  • Stretch bigs (PF/F + 33%+ from 3): {len(stretch_bigs)} players available",
            f"\nPlayers already on roster — don't duplicate these roles:",
        ] + [f"  ✓ {s}" for s in ctx["returning_strengths"]] + [
            "\nBest additions to fill Illinois's gaps:",
        ] + [
            f"  {r.player_name} ({r.position}, {r.school})\n"
            f"    Scores {r.get('ppg', 0) if hasattr(r, 'get') else getattr(r, 'ppg', 0):.1f} PPG | "
            f"3PT: {r.three_pt_pct:.1%} | "
            f"Shoots {r.ts_pct:.1%} efficiency | "
            f"Illinois system fit: {'Strong' if r.illinois_fit_score >= 65 else 'Moderate' if r.illinois_fit_score >= 50 else 'Needs work'}"
            for r in best_adds.itertuples()
        ] + [
            f"\nIf Illinois adds these 4 players, projected team stats:",
            f"  • Scoring: ~{outcomes.get('projected_ppg', 0):.1f} points per game",
            f"  • Rebounds: ~{outcomes.get('projected_rpg', 0):.1f} per game",
            f"  • 3-point shooting: {outcomes.get('team_3pt_pct', 0):.1%} as a team "
            f"({'above' if outcomes.get('team_3pt_pct', 0) >= 0.365 else 'below'} Underwood's 36.5% threshold)",
            f"  • Offensive efficiency: {outcomes.get('team_ortg', 0):.1f} (points per 100 possessions)",
            f"  • Defensive efficiency: {outcomes.get('team_drtg', 0):.1f} (lower is better)",
            f"  • Net rating: {outcomes.get('net_rating', 0):+.1f} — projected {outcomes.get('projected_wins', 20):.0f}-win season",
            f"  • Team style: {outcomes.get('team_identity', '')}",
            "\nOpen the Roster Builder to test any specific combination with the full statistical breakdown.",
        ]

        return ChatResult(
            answer="\n".join(lines),
            evidence=best_adds[["player_name", "position", "school", "illinois_fit_score", "three_pt_pct", "risk_score", "archetype"]].to_dict("records"),
            navigation=[
                {"label": "Roster Builder", "path": "/roster-builder?focused=1", "reason": "Build any lineup and see full projected stats."},
                {"label": "Recruiting Center", "path": "/recruiting-center?focused=1", "reason": "Filter portal board by specific role."},
            ],
        )

    if agent_id == "compare":
        # Handle "compare top X wings/guards/bigs"
        _pos_compare = None
        if any(t in q for t in ["wing", "forward", "sf"]): _pos_compare = ["WI", "PF"]
        elif any(t in q for t in ["guard", "pg", "sg"]): _pos_compare = ["PG", "G", "PU"]
        elif any(t in q for t in ["big", "center", "pf", "c"]): _pos_compare = ["PF", "C"]

        if _pos_compare and "compare" in q:
            pos_players = players[players["position"].isin(_pos_compare)].sort_values("illinois_fit_score", ascending=False).head(3)
            if len(pos_players) >= 2:
                lines = [f"Comparing top {pos_players.iloc[0]['position']}/{'/'.join(_pos_compare[:2])} targets:\n"]
                for r in pos_players.itertuples():
                    lines.append(
                        f"  {r.player_name} ({r.position}, {r.school})\n"
                        f"    Fit {r.illinois_fit_score:.1f} | ML success {r.transfer_success_score:.1f}% | Risk {r.risk_score:.1f} | 3PT {r.three_pt_pct:.1%}"
                    )
                best = pos_players.iloc[0]
                lines.append(f"\nRecommendation: {best['player_name']} leads on Illinois fit. Open Compare Players for full radar view.")
                return ChatResult(
                    answer="\n".join(lines),
                    evidence=pos_players.to_dict("records"),
                    navigation=[{"label": "Compare Players", "path": "/compare-players?focused=1", "reason": "Full radar comparison."}],
                )

        names = [n.strip() for n in prompt.replace("compare", "").replace("Compare", "").split(" and ") if n.strip()]
        if len(names) >= 2:
            a_df = players[players["player_name"].str.lower().str.contains(names[0].lower(), na=False)]
            b_df = players[players["player_name"].str.lower().str.contains(names[1].lower(), na=False)]
            if not a_df.empty and not b_df.empty:
                a, b = a_df.iloc[0], b_df.iloc[0]
                winner = a if a["illinois_fit_score"] >= b["illinois_fit_score"] else b
                loser = b if winner["player_name"] == a["player_name"] else a
                answer = (
                    f"{winner['player_name']} is the stronger Illinois fit.\n\n"
                    f"{a['player_name']} ({a['position']}, {a['school']}): fit {a['illinois_fit_score']:.1f}, ML success {a['transfer_success_score']:.1f}%, 3PT {a['three_pt_pct']:.1%}, risk {a['risk_score']:.1f}\n"
                    f"{b['player_name']} ({b['position']}, {b['school']}): fit {b['illinois_fit_score']:.1f}, ML success {b['transfer_success_score']:.1f}%, 3PT {b['three_pt_pct']:.1%}, risk {b['risk_score']:.1f}\n\n"
                    f"Keep {loser['player_name']} warm if timing or role negotiations shift late in the cycle."
                )
                return ChatResult(
                    answer=answer,
                    evidence=[a.to_dict(), b.to_dict()],
                    navigation=[{"label": "Compare Players", "path": "/compare-players?focused=1", "reason": "Full radar chart comparison."}],
                )
        top2 = players.sort_values("illinois_fit_score", ascending=False).head(2)
        a, b = top2.iloc[0], top2.iloc[1]
        answer = (
            f"Top-2 comparison by Illinois fit:\n\n"
            f"{a['player_name']} ({a['position']}, {a['school']}): fit {a['illinois_fit_score']:.1f}, ML success {a['transfer_success_score']:.1f}%, risk {a['risk_score']:.1f}\n"
            f"{b['player_name']} ({b['position']}, {b['school']}): fit {b['illinois_fit_score']:.1f}, ML success {b['transfer_success_score']:.1f}%, risk {b['risk_score']:.1f}\n\n"
            f"Type 'Compare [Player A] and [Player B]' to compare any specific targets."
        )
        return ChatResult(
            answer=answer,
            evidence=top2.to_dict("records"),
            navigation=[{"label": "Compare Players", "path": "/compare-players?focused=1", "reason": "Interactive radar comparison."}],
        )

    if agent_id == "risk-fit":
        best_fit = players.sort_values("illinois_fit_score", ascending=False).iloc[0]
        safest   = players.sort_values(["risk_score", "illinois_fit_score"], ascending=[True, False]).iloc[0]
        avoid    = players.sort_values("risk_score", ascending=False).head(5)
        safe_5   = players.sort_values(["risk_score", "illinois_fit_score"], ascending=[True, False]).head(5)
        risky_hi = players[(players["transfer_success_score"] > 65) & (players["risk_score"] > 50)].head(3)

        # Answer "best fit score" query
        if "best fit" in q or "highest fit" in q or "best illinois fit" in q:
            ml = ml_predict(players[players["player_name"] == best_fit["player_name"]])
            ml_str = f"{ml['transfer_success_probability']:.1f}% success" if ml else ""
            lines = [
                f"Highest Illinois Fit Score: {best_fit['player_name']} ({best_fit['position']}, {best_fit['school']})\n",
                f"  Fit Score: {best_fit['illinois_fit_score']:.1f}/100",
                f"  ML prediction: {ml_str}",
                f"  Risk: {best_fit['risk_score']:.1f}/100",
                f"  3PT: {best_fit['three_pt_pct']:.1%} | Assist rate: {best_fit.get('assist_rate', 0):.1f}% | Def rating: {best_fit.get('defensive_rating', 0):.0f}\n",
                "Why this fit score?",
                "  Illinois Fit weights: 3PT shooting, defensive rating, assist rate, and efficiency relative to Underwood's system thresholds.",
                f"  {best_fit['player_name']} grades above the 36.5% shooting threshold and profiles as a {best_fit['archetype']}.",
            ]
            return ChatResult(
                answer="\n".join(lines),
                evidence=[best_fit.to_dict()],
                navigation=[
                    {"label": "Player Intelligence", "path": "/player-intelligence?focused=1", "reason": "Full fit and risk breakdown."},
                    {"label": "Compare Players", "path": "/compare-players?focused=1", "reason": "Compare against other Tier 1 targets."},
                ],
            )

        # Answer "safest target" query
        if "safest" in q or "lowest risk" in q or "safe target" in q or "safe floor" in q:
            lines = [
                f"Safest target on the current board: {safest['player_name']} ({safest['position']}, {safest['school']})\n",
                f"  Risk Score: {safest['risk_score']:.1f}/100 (lower = safer)",
                f"  Illinois Fit: {safest['illinois_fit_score']:.1f}/100",
                f"  ML success: {safest['transfer_success_score']:.1f}%",
                f"  3PT: {safest['three_pt_pct']:.1%} | Minutes: {safest.get('minutes', 0):.0f} last season\n",
                "Safe floor board (top 5 by risk):",
            ]
            for r in safe_5.itertuples():
                lines.append(f"  {r.player_name} — risk {r.risk_score:.1f}, fit {r.illinois_fit_score:.1f}")
            return ChatResult(
                answer="\n".join(lines),
                evidence=safe_5.to_dict("records"),
                navigation=[
                    {"label": "Player Intelligence", "path": "/player-intelligence?focused=1", "reason": "Full risk score breakdown."},
                    {"label": "Recruiting Center", "path": "/recruiting-center?focused=1", "reason": "Filter by max risk."},
                ],
            )

        # Answer "risky players to avoid" query
        if "avoid" in q or "risky" in q or "red flag" in q or "stay away" in q:
            lines = ["Players to avoid or approach with caution:\n"]
            for r in avoid.itertuples():
                red_flags = []
                if r.turnover_rate > 18: red_flags.append("high TO rate")
                if r.three_pt_pct < 0.30: red_flags.append("below-threshold shooting")
                if r.defensive_rating > 107: red_flags.append("defensive liability")
                if r.minutes < 200: red_flags.append("small sample size")
                flag_str = ", ".join(red_flags) if red_flags else "general inefficiency"
                lines.append(f"  {r.player_name} ({r.school}) — risk {r.risk_score:.1f}: {flag_str}")
            lines.append("\nRisk score drives: minutes volatility, turnover rate, FT% discipline, usage mismatch. Pair with medical and background diligence.")
            return ChatResult(
                answer="\n".join(lines),
                evidence=avoid[["player_name", "risk_score", "turnover_rate", "three_pt_pct"]].to_dict("records"),
                navigation=[
                    {"label": "Player Intelligence", "path": "/player-intelligence?focused=1", "reason": "Full risk breakdown per player."},
                    {"label": "Recruiting Center", "path": "/recruiting-center?focused=1", "reason": "Set max risk filter."},
                ],
            )

        # Default risk-fit response
        lines = ["Risk & Fit Assessment:\n", "SAFE FLOOR (low risk, strong fit):"]
        for r in safe_5.head(3).itertuples():
            lines.append(f"  {r.player_name} — risk {r.risk_score:.1f}, fit {r.illinois_fit_score:.1f}, ML success {r.transfer_success_score:.1f}%")
        if not risky_hi.empty:
            lines.append("\nHIGH-CEILING / HIGH-RISK:")
            for r in risky_hi.itertuples():
                lines.append(f"  {r.player_name} — risk {r.risk_score:.1f}, upside {r.transfer_success_score:.1f}% — requires full diligence")
        lines.append("\nRisk factors: minutes volatility, turnover rate, FT% discipline, usage mismatch. Always pair with medical and background checks.")
        return ChatResult(
            answer="\n".join(lines),
            evidence=safe_5[["player_name", "risk_score", "illinois_fit_score", "transfer_success_score"]].to_dict("records"),
            navigation=[
                {"label": "Player Intelligence", "path": "/player-intelligence?focused=1", "reason": "Full risk breakdown per player."},
                {"label": "Recruiting Center", "path": "/recruiting-center?focused=1", "reason": "Filter board by max risk tolerance."},
            ],
        )

    if agent_id == "player-development":
        upside = players.sort_values(["projected_impact_score", "risk_score"], ascending=[False, True]).head(5)
        lines = ["Development priorities — ML-forecasted ceilings and improvement paths:\n"]
        for r in upside.itertuples():
            player_row = players[players["player_name"] == r.player_name]
            ml = ml_predict(player_row)
            bpm_str = f"BPM forecast {ml['future_bpm_prediction']:+.2f}" if ml else f"impact {r.projected_impact_score:.1f}"
            gaps = []
            if r.three_pt_pct < 0.33: gaps.append("3P shooting")
            if r.turnover_rate > 16:   gaps.append("turnover control")
            if r.defensive_rating > 105: gaps.append("on-ball defense")
            if r.assist_rate < 12:     gaps.append("playmaking creation")
            dev = ", ".join(gaps) if gaps else "position-specific refinement and role expansion"
            lines.append(f"  {r.player_name} ({r.archetype}) — {bpm_str} | develop: {dev}")
        lines.append("\nBPM forecasts are from the RF+XGB+MLP ensemble. Development plan assumes Illinois practice infrastructure and scheme fit.")
        return ChatResult(
            answer="\n".join(lines),
            evidence=upside[["player_name", "archetype", "projected_impact_score", "three_pt_pct", "turnover_rate", "defensive_rating"]].to_dict("records"),
            navigation=[
                {"label": "Player Intelligence", "path": "/player-intelligence?focused=1", "reason": "Full development profile per player."},
                {"label": "Roster Builder", "path": "/roster-builder?focused=1", "reason": "Project development impact on team identity."},
            ],
        )

    if agent_id == "market-inefficiency":
        board = players.sort_values(["market_inefficiency_score", "projected_impact_score"], ascending=False).head(6)
        lines = ["Market inefficiency targets — value the public is mispricing:\n"]
        for r in board.itertuples():
            lines.append(
                f"  {r.player_name} ({r.school}) — inefficiency gap {r.market_inefficiency_score:.1f}, "
                f"public rank #{r.public_transfer_rank}, projected impact {r.projected_impact_score:.1f}"
            )
        lines.append("\nThese gaps are time-sensitive. As analytics adoption grows, inefficiencies compress within 2-3 weeks of portal open.")
        return ChatResult(
            answer="\n".join(lines),
            evidence=board[["player_name", "school", "market_inefficiency_score", "public_transfer_rank", "projected_impact_score"]].to_dict("records"),
            navigation=[
                {"label": "Hidden Gem Lab", "path": "/hidden-gem-lab?focused=1", "reason": "Deep market inefficiency analysis."},
                {"label": "Recruiting Center", "path": "/recruiting-center?focused=1", "reason": "Turn market wins into contact priorities."},
            ],
        )

    if agent_id == "scenario":
        top5 = players.head(5)
        outcomes = roster_outcomes(top5)
        lines = ["Hypothetical scenario — what happens to Illinois if we add the top 5 portal targets:\n"]
        lines.append("Players in this hypothetical:")
        for _, r in top5.iterrows():
            lines.append(f"  {r['player_name']} ({r['position']}, {r['school']}) — {r.get('ppg',0):.1f} PPG, {r['three_pt_pct']:.1%} 3PT, {r.get('ts_pct',0):.1%} TS")
        lines.append("\nProjected team stats if these players join Illinois:")
        lines.append(f"  Scoring: ~{outcomes.get('projected_ppg',0):.1f} PPG (Illinois scored 78.2 PPG last season)")
        lines.append(f"  Rebounds: ~{outcomes.get('projected_rpg',0):.1f} RPG ({outcomes.get('projected_orpg',0):.1f} offensive + {outcomes.get('projected_drpg',0):.1f} defensive)")
        lines.append(f"  Assists: ~{outcomes.get('projected_apg',0):.1f} APG")
        lines.append(f"  Offensive efficiency: {outcomes.get('team_ortg',0):.1f} ORtg (points scored per 100 possessions)")
        lines.append(f"  Defensive efficiency: {outcomes.get('team_drtg',0):.1f} DRtg (points allowed per 100 possessions — lower is better)")
        lines.append(f"  Net rating: {outcomes.get('net_rating',0):+.1f} (scoring minus defense per 100 possessions)")
        lines.append(f"  3-point shooting: {outcomes.get('team_3pt_pct',0):.1%} as a team")
        lines.append(f"  Projected season: ~{outcomes.get('projected_wins',20):.0f} wins")
        lines.append(f"  Team identity: {outcomes.get('team_identity','')}")
        lines.append("\nHow win projection works: starts at 20 wins (average Big Ten team), adds/subtracts based on net rating.")
        lines.append("Each +1.5 net rating points adds roughly 1 win over a season.")
        lines.append("\nOpen the Roster Builder to test any specific combination of players with full stat breakdown.")
        return ChatResult(
            answer="\n".join(lines),
            evidence=top5[["player_name", "position", "illinois_fit_score", "risk_score"]].to_dict("records"),
            navigation=[
                {"label": "Roster Builder", "path": "/roster-builder?focused=1", "reason": "Build and simulate specific lineup combos."},
                {"label": "Recruiting Center", "path": "/recruiting-center?focused=1", "reason": "Adjust positional targets."},
            ],
        )

    if agent_id == "game-plan":
        threats = players.sort_values(["projected_impact_score", "three_pt_pct"], ascending=False).head(5)
        lines = ["Opponent threat assessment and defensive recommendations:\n"]
        for r in threats.itertuples():
            threat_type = "perimeter threat" if r.three_pt_pct > 0.37 else "drive/post threat"
            lines.append(
                f"  {r.player_name} ({r.position}, {r.school}) — {threat_type}\n"
                f"    Impact {r.projected_impact_score:.1f} | 3PT {r.three_pt_pct:.1%} | Drtg {r.defensive_rating:.0f}"
            )
        lines.append("\nAssign your best on-ball defender to the top perimeter threat. Force drives on catch-and-shoot players rather than leaving space for spot-up threes.")
        return ChatResult(
            answer="\n".join(lines),
            evidence=threats[["player_name", "school", "position", "projected_impact_score", "three_pt_pct", "defensive_rating"]].to_dict("records"),
            navigation=[
                {"label": "Scouting Center", "path": "/scouting-center?focused=1", "reason": "Full per-player scouting breakdown."},
                {"label": "Player Intelligence", "path": "/player-intelligence?focused=1", "reason": "Defensive tendency analysis."},
            ],
        )

    return None


def chat_response(prompt: str, players: pd.DataFrame, roster: pd.DataFrame, agent_id: str = "main") -> ChatResult:
    normalized = prompt.lower().strip()

    # ── Greetings / thanks → instant response (no routing needed) ──────────────
    if normalized in {"hi", "hello", "hey", "yo", "what's up", "whats up", "good morning", "good afternoon", "good evening", "thanks", "thank you", "thx", "appreciate it"}:
        return _rule_based_chat(prompt, players, roster)

    # ── Main agent: ALWAYS try routing FIRST before any other handler ──────────
    # This ensures every basketball question gets routed to the right specialist
    # instead of falling through to generic rule-based responses.
    if agent_id == "main":
        routed_id = _detect_intent(normalized)
        if routed_id:
            inner = _agent_specific_response(routed_id, prompt, players, roster)
            if inner is not None:
                return _routed_result(routed_id, inner, normalized)

        # No specific agent matched — try rule-based (handles meta-questions, off-topic, etc.)
        return _rule_based_chat(prompt, players, roster)

    # ── Specialist agent: dispatch directly to agent logic ─────────────────────
    agent_result = _agent_specific_response(agent_id, prompt, players, roster)
    if agent_result is not None:
        return agent_result

    # Gemini fallback
    settings = get_settings()
    if settings.gemini_api_key:
        try:
            from google import genai
            from google.genai import types as gtypes

            client = genai.Client(api_key=settings.gemini_api_key)

            context_players = players.sort_values("hidden_gem_score", ascending=False).head(20)[[
                "player_name", "position", "school", "public_transfer_rank",
                "transfer_success_score", "illinois_fit_score", "risk_score",
                "three_pt_pct", "defensive_rating", "market_inefficiency_score",
            ]].to_csv(index=False)

            hint = _AGENT_SYSTEM_HINTS.get(agent_id, "")
            system_prompt = (
                "You are Illinois Front Office AI — a basketball operations analyst for Illinois Men's Basketball. "
                "You are direct, specific, and data-grounded. Never speak generically. "
                "Always reference specific players and stats from the provided data. "
                "Structure your response as a basketball analyst would speak — not as a corporate template. "
                f"Agent context: {hint}"
            )

            full_prompt = f"{system_prompt}\n\nCurrent portal board:\n{context_players}\n\nQuestion: {prompt}"
            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=full_prompt,
                config=gtypes.GenerateContentConfig(temperature=0.2, max_output_tokens=520),
            )
            answer = (response.text or "").strip()
            if answer:
                return ChatResult(answer=answer, evidence=context_players.split("\n")[:5], navigation=_navigation_for_query(normalized))
        except Exception:
            pass

    # Final fallback
    return _rule_based_chat(prompt, players, roster)
