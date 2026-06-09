from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=2, max_length=1000)
    agent_id: str = "main"


class NavigationAction(BaseModel):
    label: str
    path: str
    reason: str | None = None


class ChatResponse(BaseModel):
    answer: str
    evidence: list[dict[str, object]]
    navigation: list[NavigationAction] = []
    routed_agent_id: str | None = None  # set when main agent routes to a specialist


class RecruitingQuery(BaseModel):
    position: str | None = None
    min_height: int | None = None
    conference: str | None = None
    max_risk: float = 100
    min_shooting: float = 0.0
    min_defense: float = 0.0
    min_rebounding: float = 0.0
    min_playmaking: float = 0.0


class CompareRequest(BaseModel):
    player_a: str
    player_b: str


class RosterRequest(BaseModel):
    selected_players: list[str]


class ScoutingReportResponse(BaseModel):
    player_name: str
    executive_summary: str
    strengths: str
    weaknesses: str
    projected_role: str
    development_areas: str
    illinois_fit: str
    recruiting_recommendation: str
    coach_notes: str


class PredictionResponse(BaseModel):
    transfer_success_probability: float
    future_bpm_prediction: float
    rf_bpm_prediction: float | None = None
    xgboost_bpm_prediction: float | None = None
    neural_network_bpm_prediction: float | None = None
    future_impact_score_prediction: float
    feature_importance: list[dict[str, object]]
