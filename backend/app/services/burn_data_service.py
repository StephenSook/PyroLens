"""Database-backed burn history and impact metric services."""

from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.burn import Burn
from app.models.net_positive_metric import NetPositiveMetric

logger = logging.getLogger(__name__)


def get_burn_history(
    db: Session,
    county: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
) -> dict[str, Any]:
    """Return burn history as a GeoJSON-like feature collection."""

    _validate_date_filters(from_date=from_date, to_date=to_date)

    query = _build_burn_query(db)
    normalized_county = county.strip().lower() if county and county.strip() else None
    if normalized_county:
        query = query.filter(func.lower(Burn.county) == normalized_county)
    if from_date:
        query = query.filter(Burn.burn_date >= from_date)
    if to_date:
        query = query.filter(Burn.burn_date <= to_date)

    try:
        rows = query.order_by(Burn.burn_date.desc(), Burn.id.desc()).all()
    except SQLAlchemyError as exc:
        logger.exception("Burn history query failed county=%s from_date=%s to_date=%s", county, from_date, to_date)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Burn history query failed",
        ) from exc

    return {
        "type": "FeatureCollection",
        "features": [
            _serialize_burn_feature(
                burn=burn,
                geometry_geojson=geometry_geojson,
                centroid_lat=centroid_lat,
                centroid_lon=centroid_lon,
            )
            for burn, geometry_geojson, centroid_lat, centroid_lon in rows
        ],
    }


def get_burn_by_id(db: Session, burn_id: int) -> dict[str, Any]:
    """Return a single burn as a GeoJSON-like feature."""

    try:
        row = _build_burn_query(db).filter(Burn.id == burn_id).one_or_none()
    except SQLAlchemyError as exc:
        logger.exception("Burn lookup failed burn_id=%s", burn_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Burn lookup failed",
        ) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Burn {burn_id} was not found",
        )

    burn, geometry_geojson, centroid_lat, centroid_lon = row
    return _serialize_burn_feature(
        burn=burn,
        geometry_geojson=geometry_geojson,
        centroid_lat=centroid_lat,
        centroid_lon=centroid_lon,
    )


def get_net_positive_metrics_by_burn_id(db: Session, burn_id: int) -> dict[str, Any]:
    """Return burn-linked net positive metrics."""

    try:
        metric = db.query(NetPositiveMetric).filter(NetPositiveMetric.burn_id == burn_id).one_or_none()
    except SQLAlchemyError as exc:
        logger.exception("Net positive metric lookup failed burn_id=%s", burn_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Net positive metrics query failed",
        ) from exc
    if metric is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Net positive metrics for burn {burn_id} were not found",
        )

    return {
        "burn_id": metric.burn_id,
        "co2_prevented": metric.co2_prevented,
        "prescribed_emissions": metric.prescribed_emissions,
        "wildfire_baseline_emissions": metric.wildfire_baseline_emissions,
        "biodiversity_gain_index": metric.biodiversity_gain_index,
        "fuel_load_reduction_pct": metric.fuel_load_reduction_pct,
        "vegetation_recovery_curve": metric.vegetation_recovery_curve,
    }


def _build_burn_query(db: Session):
    """Create the base burn-history query with geometry serialization helpers."""

    return db.query(
        Burn,
        func.ST_AsGeoJSON(Burn.location_geom).label("geometry_geojson"),
        func.ST_Y(func.ST_Centroid(Burn.location_geom)).label("centroid_lat"),
        func.ST_X(func.ST_Centroid(Burn.location_geom)).label("centroid_lon"),
    )


def _validate_date_filters(from_date: date | None, to_date: date | None) -> None:
    """Validate optional date filters before querying burn history."""

    if from_date and to_date and from_date > to_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="from_date must be on or before to_date",
        )


def _serialize_burn_feature(
    burn: Burn,
    geometry_geojson: str | None,
    centroid_lat: float | None,
    centroid_lon: float | None,
) -> dict[str, Any]:
    """Convert a burn row into a GeoJSON-like feature."""

    properties: dict[str, Any] = {
        "id": burn.id,
        "county": burn.county,
        "burn_date": burn.burn_date.isoformat(),
        "acreage": burn.acreage,
        "objective": burn.objective,
        "outcome": burn.outcome,
        "created_at": burn.created_at.isoformat(),
    }
    geometry = _parse_geometry(geometry_geojson)

    if geometry is None:
        logger.warning("Falling back to centroid geometry for burn_id=%s", burn.id)
        if centroid_lat is not None and centroid_lon is not None:
            properties["lat"] = float(centroid_lat)
            properties["lon"] = float(centroid_lon)
            # TODO: Replace the centroid fallback once all burn geometries are serialized directly as GeoJSON.
            geometry = {
                "type": "Point",
                "coordinates": [float(centroid_lon), float(centroid_lat)],
            }
        else:
            geometry = {"type": "GeometryCollection", "geometries": []}

    return {
        "type": "Feature",
        "geometry": geometry,
        "properties": properties,
    }


def _parse_geometry(geometry_geojson: str | None) -> dict[str, Any] | None:
    """Parse a PostGIS GeoJSON string into a Python mapping."""

    if not geometry_geojson:
        return None

    try:
        parsed_geometry = json.loads(geometry_geojson)
    except json.JSONDecodeError:
        return None

    if not isinstance(parsed_geometry, dict):
        return None
    return parsed_geometry
