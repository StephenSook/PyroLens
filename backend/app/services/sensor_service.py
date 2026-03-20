"""Service helpers for sensor node provisioning and sensor reading ingestion."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from geoalchemy2.elements import WKTElement
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.sensor_node import SensorNode
from app.models.sensor_reading import SensorReading
from app.schemas.sensor_reading import SensorReadingCreate

logger = logging.getLogger(__name__)

PLACEHOLDER_POINT_WKT = "POINT(0 0)"
PLACEHOLDER_SITE_PREFIX = "Unassigned sensor"
PLACEHOLDER_STATUS = "provisioning"


def get_or_create_sensor_node(db: Session, device_id: str) -> tuple[SensorNode, bool]:
    """Return the node for a device ID, provisioning a placeholder node if needed."""

    normalized_device_id = device_id.strip()
    try:
        sensor_node = db.query(SensorNode).filter(SensorNode.device_id == normalized_device_id).one_or_none()
        if sensor_node is not None:
            return sensor_node, False

        sensor_node = SensorNode(
            device_id=normalized_device_id,
            location_geom=WKTElement(PLACEHOLDER_POINT_WKT, srid=4326),
            site_name=f"{PLACEHOLDER_SITE_PREFIX} {normalized_device_id}",
            status=PLACEHOLDER_STATUS,
        )
        db.add(sensor_node)
        db.flush()
        return sensor_node, True
    except SQLAlchemyError as exc:
        logger.exception("Sensor node lookup/create failed device_id=%s", normalized_device_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sensor node lookup failed",
        ) from exc


def create_sensor_reading(db: Session, payload: SensorReadingCreate, sensor_id: int) -> SensorReading:
    """Insert a sensor reading row for an existing sensor node."""

    raw_payload = payload.model_dump(mode="json")
    sensor_reading = SensorReading(
        sensor_id=sensor_id,
        timestamp=payload.timestamp,
        temperature=payload.temperature,
        humidity=payload.humidity,
        soil_moisture=payload.soil_moisture,
        wind_speed=payload.wind_speed,
        raw_payload=raw_payload,
    )

    try:
        db.add(sensor_reading)
        db.commit()
        db.refresh(sensor_reading)
        return sensor_reading
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Sensor reading insert failed sensor_id=%s timestamp=%s", sensor_id, payload.timestamp)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sensor reading insert failed",
        ) from exc


def get_sensor_node_coordinates(db: Session, sensor_id: int) -> tuple[float, float] | None:
    """Return a node's latitude/longitude when a non-placeholder location exists."""

    try:
        row = (
            db.query(
                func.ST_Y(SensorNode.location_geom).label("lat"),
                func.ST_X(SensorNode.location_geom).label("lon"),
            )
            .filter(SensorNode.id == sensor_id)
            .one_or_none()
        )
    except SQLAlchemyError as exc:
        logger.exception("Sensor node coordinate lookup failed sensor_id=%s", sensor_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sensor node coordinate lookup failed",
        ) from exc

    if row is None or row.lat is None or row.lon is None:
        return None

    lat = float(row.lat)
    lon = float(row.lon)
    if lat == 0.0 and lon == 0.0:
        return None
    return lat, lon


def build_prediction_seed(
    *,
    temperature: float,
    humidity: float,
    soil_moisture: float,
    wind_speed: float | None,
    timestamp: datetime,
    latitude: float,
    longitude: float,
) -> dict[str, float | int]:
    """Build a minimal feature seed for an optional background ML prediction."""

    return {
        "temperature": temperature,
        "humidity": humidity,
        "wind_speed": 0.0 if wind_speed is None else float(wind_speed),
        "soil_moisture": soil_moisture,
        "ndvi": 0.5,
        "fuel_load_estimate": 50.0,
        "time_since_last_burn_days": 365.0,
        "latitude": latitude,
        "longitude": longitude,
        "month": timestamp.month,
    }
