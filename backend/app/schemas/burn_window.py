"""Pydantic schemas for burn-window prediction payloads."""

from pydantic import BaseModel

from app.ml.model import BurnWindowFeatures


class BurnWindowRequest(BurnWindowFeatures):
    """Request payload for burn-window prediction."""


class BurnWindowResponse(BaseModel):
    """Normalized response payload returned by the burn-window API."""

    score: int
    recommendation: str
    prob_success: float
    raw_probability: float
