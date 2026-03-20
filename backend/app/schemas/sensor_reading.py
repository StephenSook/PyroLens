"""Pydantic schemas for sensor reading payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SensorReadingCreate(BaseModel):
    """Payload used when ingesting a reading from a device."""

    device_id: str = Field(min_length=1, max_length=255)
    temperature: float = Field(ge=-80.0, le=160.0)
    humidity: float = Field(ge=0.0, le=100.0)
    soil_moisture: float = Field(ge=0.0, le=100.0)
    wind_speed: float | None = Field(default=None, ge=0.0, le=200.0)
    timestamp: datetime


class SensorReading(BaseModel):
    """API response matching the persisted sensor_readings table."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    sensor_id: int
    timestamp: datetime
    temperature: float
    humidity: float
    soil_moisture: float
    wind_speed: float | None = None
    raw_payload: dict[str, Any]
