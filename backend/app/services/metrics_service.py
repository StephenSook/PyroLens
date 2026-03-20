"""Net-positive metrics calculation and persistence helpers."""

from __future__ import annotations

import logging
from datetime import date, datetime, time
from statistics import mean
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.burn import Burn
from app.models.net_positive_metric import NetPositiveMetric
from app.schemas.net_positive_metric import NetPositiveMetricsResponse
from app.services import sentinel_client

logger = logging.getLogger(__name__)

DEFAULT_BIODIVERSITY_GAIN_INDEX = 0.55
DEFAULT_FUEL_LOAD_REDUCTION_PCT = 40.0


async def get_or_create_net_positive_metrics(db: Session, burn_id: int) -> NetPositiveMetricsResponse:
    """Return cached burn metrics or compute and persist them on demand."""

    burn, metric, centroid_lat, centroid_lon = _get_burn_and_metric(db, burn_id=burn_id)
    if metric is not None:
        return _build_response(metric)

    if centroid_lat is None or centroid_lon is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Burn {burn_id} does not have a usable geometry centroid",
        )

    vegetation_recovery_curve = await _fetch_vegetation_recovery_curve(
        lat=float(centroid_lat),
        lon=float(centroid_lon),
        burn_date=burn.burn_date,
    )
    wildfire_baseline_emissions, prescribed_emissions, co2_prevented = _calculate_emissions(burn.acreage)
    biodiversity_gain_index = _derive_biodiversity_gain_index(burn=burn, recovery_curve=vegetation_recovery_curve)
    fuel_load_reduction_pct = _derive_fuel_load_reduction_pct(burn=burn, recovery_curve=vegetation_recovery_curve)

    metric = _persist_metric(
        db,
        burn_id=burn.id,
        co2_prevented=co2_prevented,
        prescribed_emissions=prescribed_emissions,
        wildfire_baseline_emissions=wildfire_baseline_emissions,
        biodiversity_gain_index=biodiversity_gain_index,
        fuel_load_reduction_pct=fuel_load_reduction_pct,
        vegetation_recovery_curve=vegetation_recovery_curve,
    )
    return _build_response(metric)


def _get_burn_and_metric(
    db: Session,
    *,
    burn_id: int,
) -> tuple[Burn, NetPositiveMetric | None, float | None, float | None]:
    """Load the burn, any persisted metrics row, and centroid coordinates."""

    try:
        row = (
            db.query(
                Burn,
                NetPositiveMetric,
                func.ST_Y(func.ST_Centroid(Burn.location_geom)).label("centroid_lat"),
                func.ST_X(func.ST_Centroid(Burn.location_geom)).label("centroid_lon"),
            )
            .outerjoin(NetPositiveMetric, NetPositiveMetric.burn_id == Burn.id)
            .filter(Burn.id == burn_id)
            .order_by(NetPositiveMetric.id.desc())
            .first()
        )
    except SQLAlchemyError as exc:
        logger.exception("Net-positive metric lookup failed burn_id=%s", burn_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Net positive metrics query failed",
        ) from exc

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Burn {burn_id} was not found",
        )

    burn, metric, centroid_lat, centroid_lon = row
    return burn, metric, centroid_lat, centroid_lon


async def _fetch_vegetation_recovery_curve(
    *,
    lat: float,
    lon: float,
    burn_date: date,
) -> list[dict[str, Any]]:
    """Fetch and normalize the burn's NDVI recovery curve."""

    start_date = min(burn_date, date.today())
    end_date = date.today()

    try:
        series = await sentinel_client.get_ndvi_timeseries(
            lat=lat,
            lon=lon,
            start_date=start_date,
            end_date=end_date,
        )
    except HTTPException as exc:
        logger.warning(
            "NDVI lookup failed for net-positive metrics lat=%s lon=%s burn_date=%s detail=%s",
            lat,
            lon,
            burn_date,
            exc.detail,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="NDVI data unavailable for burn metrics",
        ) from exc
    except Exception as exc:
        logger.exception(
            "Unexpected NDVI lookup failure for net-positive metrics lat=%s lon=%s burn_date=%s",
            lat,
            lon,
            burn_date,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="NDVI data unavailable for burn metrics",
        ) from exc

    normalized_curve = _normalize_vegetation_recovery_curve(series)
    if not normalized_curve:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="NDVI data unavailable for burn metrics",
        )
    return normalized_curve


def _normalize_vegetation_recovery_curve(raw_curve: Any) -> list[dict[str, Any]]:
    """Normalize NDVI points for JSONB storage and schema validation."""

    if not isinstance(raw_curve, list):
        return []

    normalized_points: list[dict[str, Any]] = []
    for point in raw_curve:
        if not isinstance(point, dict):
            continue

        timestamp = _coerce_timestamp(point.get("timestamp"))
        ndvi_value = point.get("ndvi")
        if timestamp is None or ndvi_value is None:
            continue

        normalized_points.append(
            {
                "timestamp": timestamp.isoformat(),
                "ndvi": round(float(ndvi_value), 4),
            }
        )
    return normalized_points


def _coerce_timestamp(value: Any) -> datetime | None:
    """Coerce a date-like value into a datetime for NDVI schema compatibility."""

    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, time.min)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            try:
                return datetime.combine(date.fromisoformat(value.split("T", 1)[0]), time.min)
            except ValueError:
                return None
    return None


def _calculate_emissions(acreage: float) -> tuple[float, float, float]:
    """Calculate baseline wildfire emissions, prescribed emissions, and avoided CO2."""

    normalized_acreage = max(float(acreage), 0.0)
    wildfire_baseline_emissions = round(
        normalized_acreage * settings.WILDFIRE_BASELINE_EMISSIONS_PER_ACRE,
        4,
    )
    prescribed_emissions = round(
        normalized_acreage * settings.PRESCRIBED_BURN_EMISSIONS_PER_ACRE,
        4,
    )
    co2_prevented = round(max(wildfire_baseline_emissions - prescribed_emissions, 0.0), 4)
    return wildfire_baseline_emissions, prescribed_emissions, co2_prevented


def _derive_biodiversity_gain_index(
    *,
    burn: Burn,
    recovery_curve: list[dict[str, Any]],
) -> float:
    """Estimate biodiversity gain using NDVI recovery plus simple burn metadata heuristics."""

    if not recovery_curve:
        return DEFAULT_BIODIVERSITY_GAIN_INDEX

    ndvi_values = [float(point["ndvi"]) for point in recovery_curve]
    average_ndvi = mean(ndvi_values)
    peak_ndvi = max(ndvi_values)
    biodiversity_gain = 0.25 + (average_ndvi * 0.35) + (peak_ndvi * 0.25)
    if _has_positive_outcome(burn.outcome):
        biodiversity_gain += 0.08
    if _mentions_restoration_goal(burn.objective):
        biodiversity_gain += 0.07
    return round(min(max(biodiversity_gain, 0.0), 1.0), 3)


def _derive_fuel_load_reduction_pct(
    *,
    burn: Burn,
    recovery_curve: list[dict[str, Any]],
) -> float:
    """Estimate percent fuel-load reduction from available ecological signals."""

    if not recovery_curve:
        return DEFAULT_FUEL_LOAD_REDUCTION_PCT

    ndvi_values = [float(point["ndvi"]) for point in recovery_curve]
    min_ndvi = min(ndvi_values)
    latest_ndvi = ndvi_values[-1]
    initial_ndvi = ndvi_values[0]

    reduction_pct = (1.0 - min_ndvi) * 55.0
    reduction_pct += max(initial_ndvi - latest_ndvi, 0.0) * 25.0
    if "fuel" in burn.objective.lower():
        reduction_pct += 10.0
    if _has_positive_outcome(burn.outcome):
        reduction_pct += 5.0
    return round(min(max(reduction_pct, 0.0), 100.0), 2)


def _has_positive_outcome(outcome: str) -> bool:
    """Return whether the burn outcome suggests a successful operation."""

    normalized = outcome.strip().lower()
    return normalized in {"successful", "success", "complete", "completed", "optimal"}


def _mentions_restoration_goal(objective: str) -> bool:
    """Return whether the burn objective implies ecological restoration work."""

    normalized = objective.strip().lower()
    return any(keyword in normalized for keyword in ("restore", "restoration", "habitat", "ecosystem", "biodiversity"))


def _persist_metric(
    db: Session,
    *,
    burn_id: int,
    co2_prevented: float,
    prescribed_emissions: float,
    wildfire_baseline_emissions: float,
    biodiversity_gain_index: float,
    fuel_load_reduction_pct: float,
    vegetation_recovery_curve: list[dict[str, Any]],
) -> NetPositiveMetric:
    """Persist a newly computed net-positive metric row."""

    metric = NetPositiveMetric(
        burn_id=burn_id,
        co2_prevented=co2_prevented,
        prescribed_emissions=prescribed_emissions,
        wildfire_baseline_emissions=wildfire_baseline_emissions,
        biodiversity_gain_index=biodiversity_gain_index,
        fuel_load_reduction_pct=fuel_load_reduction_pct,
        vegetation_recovery_curve=vegetation_recovery_curve,
    )

    try:
        db.add(metric)
        db.commit()
        db.refresh(metric)
        return metric
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Net-positive metric persistence failed burn_id=%s", burn_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Net positive metrics persistence failed",
        ) from exc


def _build_response(metric: NetPositiveMetric) -> NetPositiveMetricsResponse:
    """Convert an ORM metric row into the public response schema."""

    return NetPositiveMetricsResponse(
        burn_id=metric.burn_id,
        co2_prevented=float(metric.co2_prevented),
        prescribed_emissions=float(metric.prescribed_emissions),
        wildfire_baseline_emissions=float(metric.wildfire_baseline_emissions),
        biodiversity_gain_index=float(metric.biodiversity_gain_index),
        fuel_load_reduction_pct=float(metric.fuel_load_reduction_pct),
        vegetation_recovery_curve=_normalize_vegetation_recovery_curve(metric.vegetation_recovery_curve),
    )
