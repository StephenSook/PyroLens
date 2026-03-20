"""Pydantic schemas for sensor reading payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class SensorReadingCreate(BaseModel):
    """Payload used when ingesting a reading from a device."""

    device_id: str
    temperature: float
    humidity: float
    soil_moisture: float
    wind_speed: float | None = None
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
