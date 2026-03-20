"""Pydantic schemas for net positive impact metrics."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.schemas.ndvi import NDVIPoint


class NetPositiveMetricsResponse(BaseModel):
    """Response payload for net positive impact metrics."""

    model_config = ConfigDict(from_attributes=True)

    burn_id: int
    co2_prevented: float
    prescribed_emissions: float
    wildfire_baseline_emissions: float
    biodiversity_gain_index: float
    fuel_load_reduction_pct: float
    vegetation_recovery_curve: list[NDVIPoint]
