from __future__ import annotations

from pydantic import BaseModel


class ScoreComponents(BaseModel):
    demand_score: float
    growth_score: float
    competition_score: float
    margin_score: float
    pain_point_score: float
    risk_score: float
    confidence_score: float
    final_score: float
    recommendation: str
    explanation: str
    score_breakdown: dict

