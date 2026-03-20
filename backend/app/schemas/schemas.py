"""Shared API response schemas."""

from __future__ import annotations

from datetime import date
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


class NDVIPoint(BaseModel):
    """Single NDVI observation for a location and date."""

    timestamp: str
    ndvi: float


class NDVIResponse(BaseModel):
    """NDVI time-series response payload exposed by the API."""

    lat: float
    lon: float
    start_date: date
    end_date: date
    points: list[NDVIPoint]
    peak_ndvi: float
    recovery_months: int
