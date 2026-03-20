"""Pydantic schemas for burn history GeoJSON payloads."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel


class BurnHistoryGeometry(BaseModel):
    """GeoJSON geometry payload for a burn feature."""

    type: str
    coordinates: Any


class BurnHistoryProperties(BaseModel):
    """Burn metadata derived from the burns table."""

    id: int
    county: str
    burn_date: date
    acreage: float
    objective: str
    outcome: str
    created_at: datetime


class BurnHistoryItem(BaseModel):
    """Single GeoJSON Feature for a burn history record."""

    type: Literal["Feature"] = "Feature"
    geometry: BurnHistoryGeometry
    properties: BurnHistoryProperties


class BurnHistoryResponse(BaseModel):
    """GeoJSON FeatureCollection response for burn history endpoints."""

    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[BurnHistoryItem]
