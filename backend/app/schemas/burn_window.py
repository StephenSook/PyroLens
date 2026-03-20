"""Pydantic schemas for burn window recommendation payloads."""

from datetime import date as date_type
from datetime import datetime

from pydantic import BaseModel


class BurnWindowRequest(BaseModel):
    """Internal request payload for burn window scoring."""

    lat: float
    lon: float
    date: date_type | None = None


class BurnConditions(BaseModel):
    """Environmental inputs returned with a burn recommendation."""

    temperature: float
    humidity: float
    wind_speed: float
    soil_moisture: float


class BurnWindowResponse(BaseModel):
    """Burn window response payload exposed by the API."""

    burn_score: int
    recommendation: str
    conditions: BurnConditions
    next_optimal_window: datetime | None = None
