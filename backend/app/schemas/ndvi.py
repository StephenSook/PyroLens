"""Pydantic schemas for NDVI time-series responses."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, RootModel


class NDVIPoint(BaseModel):
    """Single NDVI observation."""

    timestamp: datetime
    ndvi: float


class NDVIResponse(RootModel[list[NDVIPoint]]):
    """List response returned by the NDVI endpoint."""
