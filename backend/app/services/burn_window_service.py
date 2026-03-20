"""Service helpers for location-based burn-window prediction."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.burn import Burn
from app.models.burn_window_score import BurnWindowScore
from app.models.sensor_node import SensorNode
from app.models.sensor_reading import SensorReading

logger = logging.getLogger(__name__)

DEFAULT_SENSOR_RADIUS_METERS = 50_000


def get_latest_nearby_sensor_reading(
    db: Session,
    lat: float,
    lon: float,
    radius_meters: int = DEFAULT_SENSOR_RADIUS_METERS,
) -> SensorReading | None:
    """Return the latest reading from the nearest sensor within the given radius."""

    point = _build_point(lon=lon, lat=lat)
    distance_expr = func.ST_DistanceSphere(SensorNode.location_geom, point)

    try:
        return (
            db.query(SensorReading)
            .join(SensorReading.sensor_node)
            .filter(distance_expr <= radius_meters)
            .order_by(distance_expr.asc(), SensorReading.timestamp.desc())
            .first()
        )
    except SQLAlchemyError as exc:
        logger.exception("Nearby sensor lookup failed lat=%s lon=%s radius_meters=%s", lat, lon, radius_meters)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Nearby sensor lookup failed",
        ) from exc


def get_relevant_burn_for_location(db: Session, lat: float, lon: float) -> Burn | None:
    """Return the latest burn covering a point or the nearest burn if none covers it."""

    point = _build_point(lon=lon, lat=lat)

    try:
        covering_burn = (
            db.query(Burn)
            .filter(func.ST_Covers(Burn.location_geom, point))
            .order_by(Burn.burn_date.desc(), Burn.id.desc())
            .first()
        )
        if covering_burn is not None:
            return covering_burn

        distance_expr = func.ST_DistanceSphere(func.ST_Centroid(Burn.location_geom), point)
        return (
            db.query(Burn)
            .order_by(distance_expr.asc(), Burn.burn_date.desc(), Burn.id.desc())
            .first()
        )
    except SQLAlchemyError as exc:
        logger.exception("Burn lookup by location failed lat=%s lon=%s", lat, lon)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Burn lookup failed",
        ) from exc


def create_burn_window_score(
    db: Session,
    *,
    lat: float,
    lon: float,
    score: int,
    recommendation: str,
    conditions: dict[str, Any],
    burn_id: int | None = None,
    source: str = "ml",
) -> BurnWindowScore:
    """Persist a burn-window score row and return the saved ORM object."""

    score_row = BurnWindowScore(
        burn_id=burn_id,
        lat=lat,
        lon=lon,
        score=score,
        recommendation=recommendation,
        source=source,
        conditions=conditions,
    )

    try:
        db.add(score_row)
        db.commit()
        db.refresh(score_row)
        return score_row
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Burn-window score persistence failed lat=%s lon=%s", lat, lon)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Burn window score persistence failed",
        ) from exc


def _build_point(*, lon: float, lat: float):
    """Build an SRID 4326 point geometry from longitude and latitude."""

    return func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326)
