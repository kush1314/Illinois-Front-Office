import os

import pandas as pd
from dotenv import load_dotenv

from utils.scouting_report import scouting_snapshot


load_dotenv()


def _dataset_context(players: pd.DataFrame, limit: int = 12) -> str:
    cols = [
        "player_name",
        "school",
        "position",
        "public_rank",
        "hidden_gem_score",
        "transfer_success_score",
        "illinois_fit_score",
        "risk_score",
        "three_pt_pct",
        "assist_rate",
        "defensive_rebound_rate",
        "block_rate",
    ]
    return players.sort_values("hidden_gem_score", ascending=False).head(limit)[cols].to_csv(index=False)


def _rule_based_answer(prompt: str, players: pd.DataFrame) -> str:
    lower = prompt.lower()
    if ("top-3" in lower or "top 3" in lower or "class" in lower or "build" in lower) and len(players) >= 3:
        pool = players.head(3)
        avg_fit = pool["illinois_fit_score"].mean()
        avg_risk = pool["risk_score"].mean()
        identity = pool["primary_skill"].mode().iloc[0]
        lines = [
            "Recommendation:",
            f"Build the class around {', '.join(pool['player_name'].tolist())}. This group averages {avg_fit:.1f} Illinois fit with {avg_risk:.1f} risk, giving the staff a {identity.lower()}-leaning portal identity.",
            "",
            "Staff use:",
        ]
        for _, row in pool.iterrows():
            lines.append(
                f"- {row['player_name']} ({row['school']}) gives {row['primary_skill'].lower()} value: "
                f"{row['hidden_gem_score']:.1f} hidden gem, {row['transfer_success_score']:.1f} success, {row['risk_score']:.1f} risk."
            )
        lines.append("\nConcern: Do not treat the trio as final until the staff validates role acceptance, medicals, and defensive film.")
        return "\n".join(lines)
    if "compare" in lower and len(players) >= 2:
        a, b = players.iloc[0], players.iloc[1]
        return (
            f"Recommendation: {a['player_name']} is the cleaner Illinois target over {b['player_name']} because "
            f"his hidden gem score is {a['hidden_gem_score']:.1f} versus {b['hidden_gem_score']:.1f}, with a "
            f"{a['illinois_fit_score']:.1f} fit score and {a['risk_score']:.1f} risk score. "
            f"He also brings {a['primary_skill'].lower()} as the clearest bankable skill.\n\n"
            f"Concern: {b['player_name']} may still be worth tracking if the staff wants a different role profile or if the market price is better."
        )
    if "risk" in lower or "upside" in lower:
        pool = players[(players["transfer_success_score"] > 60) & (players["risk_score"] > 50)].head(3)
    elif "3&d" in lower or "wing" in lower or "defense" in lower:
        pool = players[(players["position"].isin(["W", "F"])) & (players["three_pt_pct"] >= 0.35)].head(3)
    elif "fit" in lower or "illinois" in lower:
        pool = players.sort_values("illinois_fit_score", ascending=False).head(3)
    elif "report" in lower or "scouting" in lower:
        return scouting_snapshot(players.iloc[0])
    else:
        pool = players.head(3)

    if pool.empty:
        pool = players.head(3)
    lines = ["Recommendation:"]
    for _, row in pool.iterrows():
        lines.append(
            f"- {row['player_name']} ({row['school']}) | hidden gem {row['hidden_gem_score']:.1f}, "
            f"fit {row['illinois_fit_score']:.1f}, success {row['transfer_success_score']:.1f}, risk {row['risk_score']:.1f}. "
            f"Stats used: {row['three_pt_pct']:.1%} 3P, {row['assist_rate']:.1f}% AST, {row['defensive_rebound_rate']:.1f}% DRB, {row['block_rate']:.1f}% BLK."
        )
    lines.append("\nNext staff action: put these names into the watchlist, compare the top two by role, then generate a scouting report for the best fit.")
    lines.append("\nConcern: Use this as a shortlist, then validate role, medicals, and film context before prioritizing calls.")
    return "\n".join(lines)


def answer_prompt(prompt: str, players: pd.DataFrame) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return _rule_based_answer(prompt, players)

    try:
        from google import genai
        from google.genai import types as gtypes

        client = genai.Client(api_key=api_key)
        full_prompt = (
            "You are PortalGPT, a concise college basketball front-office assistant. "
            "Answer only from the provided dataset context. Cite the stats used. "
            "Use coach-friendly language with Recommendation and Concern sections.\n\n"
            f"Dataset:\n{_dataset_context(players)}\n\nQuestion: {prompt}"
        )
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=full_prompt,
            config=gtypes.GenerateContentConfig(temperature=0.25, max_output_tokens=450),
        )
        return (response.text or "").strip() or _rule_based_answer(prompt, players)
    except Exception as exc:
        return f"{_rule_based_answer(prompt, players)}\n\nGemini fallback note: {exc}"
