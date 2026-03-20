"""Shared API response schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class BurnWindowConditions(BaseModel):
    """Current environmental conditions included in a burn-window response."""

    temperature: float
    humidity: float
    wind_speed: float
    soil_moisture: float


class BurnWindowResponse(BaseModel):
    """Location-based burn-window response payload exposed by the API."""

    burn_score: int
    recommendation: str
    conditions: BurnWindowConditions
    next_optimal_window: str | None = None
    sensor_data: Literal["live", "unavailable"]
    ndvi: float
    model_source: Literal["ml"]
