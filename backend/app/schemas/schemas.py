"""Shared API response schemas."""

from __future__ import annotations

from datetime import date, datetime
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
    sensor_timestamp: datetime | None = None
    sensor_device_id: str | None = None
    matched_burn_id: int | None = None
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
    buffer_meters: int
    series: list[NDVIPoint]


class FireDetection(BaseModel):
    """Single NASA FIRMS fire detection."""

    latitude: float
    longitude: float
    frp: float | None = None
    confidence: str | None = None
    acq_date: str | None = None
    acq_time: str | None = None
    satellite: str | None = None


class ActiveFiresResponse(BaseModel):
    """Active fire detections for a bounding box."""

    bbox: str
    day_range: int
    source: str
    count: int
    fires: list[FireDetection]
