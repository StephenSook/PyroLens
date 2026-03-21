"""Sensor ingestion endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.ml.model import BurnWindowFeatures, burn_window_model
from app.schemas.sensor_reading import SensorReading, SensorReadingCreate
from app.services.sensor_service import (
    build_prediction_seed,
    create_sensor_reading,
    get_or_create_sensor_node,
    get_sensor_node_coordinates,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Sensors"])


@router.post("/sensors/data", response_model=SensorReading)
async def create_sensor_data(
    payload: SensorReadingCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> SensorReading:
    """Ingest a sensor reading, provisioning the node when necessary."""

    sensor_node, was_created = get_or_create_sensor_node(db, payload.device_id)
    if was_created:
        logger.info("Provisioned placeholder sensor node for device_id=%s", payload.device_id)

    created_reading = create_sensor_reading(db, payload, sensor_node.id)

    coordinates = get_sensor_node_coordinates(db, sensor_node.id)
    if coordinates is not None:
        latitude, longitude = coordinates
        prediction_seed = build_prediction_seed(
            temperature=payload.temperature,
            humidity=payload.humidity,
            soil_moisture=payload.soil_moisture,
            wind_speed=payload.wind_speed,
            timestamp=payload.timestamp,
            latitude=latitude,
            longitude=longitude,
        )
        background_tasks.add_task(_run_background_prediction, payload.device_id, prediction_seed)
    else:
        logger.info(
            "Skipping background burn-window prediction for device_id=%s because location is unavailable",
            payload.device_id,
        )

    return SensorReading.model_validate(created_reading)


def _run_background_prediction(device_id: str, prediction_seed: dict[str, float | int]) -> None:
    """Run a lightweight background prediction for a sensor node when coordinates exist."""

    try:
        prediction = burn_window_model.predict(BurnWindowFeatures(**prediction_seed))
        logger.info(
            "Background burn-window prediction complete device_id=%s recommendation=%s score=%s",
            device_id,
            prediction["recommendation"],
            prediction["score"],
        )
    except Exception:
        logger.exception("Background burn-window prediction failed device_id=%s", device_id)
