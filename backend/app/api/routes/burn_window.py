"""Burn-window prediction endpoints."""

from __future__ import annotations

import logging
from datetime import date as date_type
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.ml.model import BurnWindowFeatures, burn_window_model
from app.schemas.burn_window import BurnWindowPredictionResponse, BurnWindowRequest
from app.schemas.schemas import BurnWindowConditions, BurnWindowResponse
from app.services import sentinel_client, weather_client
from app.services.burn_window_service import (
    create_burn_window_score,
    get_latest_nearby_sensor_reading,
    get_relevant_burn_for_location,
)

logger = logging.getLogger(__name__)

DEFAULT_SOIL_MOISTURE = 25.0
DEFAULT_NDVI = 0.5
DEFAULT_TIME_SINCE_LAST_BURN_DAYS = 365.0
DEFAULT_FUEL_LOAD_ESTIMATE = 50.0

router = APIRouter(tags=["Burn Window"])


@router.post("/burn-window/predict", response_model=BurnWindowPredictionResponse)
def predict_burn_window(features: BurnWindowRequest) -> BurnWindowPredictionResponse:
    """Predict burn-window success from a direct ML feature payload."""

    prediction = burn_window_model.predict(features)
    return BurnWindowPredictionResponse(**prediction)


@router.get("/burn-window", response_model=BurnWindowResponse)
async def get_burn_window(
    lat: float,
    lon: float,
    date: date_type | None = Query(default=None),
    db: Session = Depends(get_db),
) -> BurnWindowResponse:
    """Compute a burn-window recommendation for a location using live backend inputs."""

    requested_date = date or date_type.today()

    try:
        weather_data = await weather_client.get_current_and_forecast(lat, lon)
        temperature = float(weather_data["temperature"])
        humidity = float(weather_data["humidity"])
        wind_speed = float(weather_data["wind_speed"])
        forecast_periods = weather_data.get("forecast_periods", [])
    except HTTPException as exc:
        if exc.status_code == status.HTTP_400_BAD_REQUEST:
            raise
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Weather data unavailable, cannot compute burn window",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected weather lookup failure lat=%s lon=%s", lat, lon)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Weather data unavailable, cannot compute burn window",
        ) from exc

    soil_moisture = DEFAULT_SOIL_MOISTURE
    sensor_data = "unavailable"
    sensor_timestamp = None
    sensor_device_id = None
    try:
        sensor_reading = get_latest_nearby_sensor_reading(db, lat=lat, lon=lon)
        if sensor_reading is None:
            logger.warning("No nearby sensor reading found lat=%s lon=%s; using default soil moisture", lat, lon)
        else:
            soil_moisture = float(sensor_reading.soil_moisture)
            sensor_data = "live"
            sensor_timestamp = sensor_reading.timestamp
            sensor_device_id = sensor_reading.sensor_node.device_id if sensor_reading.sensor_node is not None else None
    except Exception:
        logger.warning("Sensor lookup failed lat=%s lon=%s; using default soil moisture", lat, lon, exc_info=True)

    ndvi = DEFAULT_NDVI
    ndvi_start_date = requested_date - timedelta(days=30)
    try:
        ndvi_series = await sentinel_client.get_ndvi_timeseries(
            lat=lat,
            lon=lon,
            start_date=ndvi_start_date,
            end_date=requested_date,
        )
        latest_ndvi = _extract_latest_ndvi(ndvi_series)
        if latest_ndvi is None:
            logger.warning("No NDVI observations found lat=%s lon=%s; using default NDVI", lat, lon)
        else:
            ndvi = latest_ndvi
    except Exception:
        logger.warning("NDVI lookup failed lat=%s lon=%s; using default NDVI", lat, lon, exc_info=True)

    time_since_last_burn_days = DEFAULT_TIME_SINCE_LAST_BURN_DAYS
    matched_burn_id: int | None = None
    try:
        burn = get_relevant_burn_for_location(db, lat=lat, lon=lon)
        if burn is None:
            logger.warning("No historical burn found lat=%s lon=%s; using default burn recency", lat, lon)
        else:
            matched_burn_id = int(burn.id)
            elapsed_days = (date_type.today() - burn.burn_date).days
            time_since_last_burn_days = float(max(elapsed_days, 0))
    except Exception:
        logger.warning("Burn history lookup failed lat=%s lon=%s; using default burn recency", lat, lon, exc_info=True)

    fuel_load_estimate = _derive_fuel_load_estimate(ndvi)
    features = BurnWindowFeatures(
        temperature=temperature,
        humidity=humidity,
        wind_speed=wind_speed,
        soil_moisture=soil_moisture,
        ndvi=ndvi,
        fuel_load_estimate=fuel_load_estimate,
        time_since_last_burn_days=time_since_last_burn_days,
        latitude=lat,
        longitude=lon,
        month=requested_date.month,
    )

    try:
        prediction = burn_window_model.predict(features)
    except Exception as exc:
        logger.exception("Burn-window model inference failed lat=%s lon=%s", lat, lon)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Model inference failed",
        ) from exc

    conditions = BurnWindowConditions(
        temperature=temperature,
        humidity=humidity,
        wind_speed=wind_speed,
        soil_moisture=soil_moisture,
    )
    next_optimal_window = _find_next_optimal_window(
        forecast_periods=forecast_periods,
        fallback_humidity=humidity,
        requested_date=requested_date,
    )

    response = BurnWindowResponse(
        burn_score=int(prediction["score"]),
        recommendation=str(prediction["recommendation"]),
        conditions=conditions,
        next_optimal_window=next_optimal_window,
        sensor_data=sensor_data,
        sensor_timestamp=sensor_timestamp,
        sensor_device_id=sensor_device_id,
        matched_burn_id=matched_burn_id,
        ndvi=ndvi,
        model_source="ml",
    )

    persisted_conditions: dict[str, Any] = {
        **conditions.model_dump(),
        "ndvi": ndvi,
        "fuel_load_estimate": fuel_load_estimate,
        "time_since_last_burn_days": time_since_last_burn_days,
        "sensor_data": sensor_data,
        "model_source": "ml",
        "month": requested_date.month,
        "prob_success": prediction.get("prob_success"),
        "raw_probability": prediction.get("raw_probability"),
    }
    create_burn_window_score(
        db,
        lat=lat,
        lon=lon,
        score=response.burn_score,
        recommendation=response.recommendation,
        conditions=persisted_conditions,
        burn_id=matched_burn_id,
        source="ml",
    )
    return response


def _extract_latest_ndvi(ndvi_series: list[dict[str, Any]]) -> float | None:
    """Return the most recent NDVI value from a normalized Sentinel time series."""

    if not ndvi_series:
        return None
    latest = ndvi_series[-1].get("ndvi")
    if latest is None:
        return None
    return float(latest)


def _derive_fuel_load_estimate(ndvi: float) -> float:
    """Approximate fuel load from NDVI on a 0-100 scale."""

    if ndvi < 0:
        return 0.0
    if ndvi > 1:
        return DEFAULT_FUEL_LOAD_ESTIMATE
    return round(ndvi * 100.0, 2)


def _find_next_optimal_window(
    forecast_periods: list[dict[str, Any]],
    fallback_humidity: float,
    requested_date: date_type,
) -> str | None:
    """Return the first forecast date that falls within the safe operating ranges."""

    for period in forecast_periods:
        start_time = period.get("start_time")
        if not isinstance(start_time, str):
            continue

        try:
            forecast_datetime = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        except ValueError:
            continue

        forecast_date = forecast_datetime.date()
        if forecast_date < requested_date:
            continue

        temperature = _coerce_forecast_temperature(period)
        wind_speed = _coerce_float(period.get("wind_speed"))
        humidity = _coerce_float(period.get("humidity"))
        effective_humidity = fallback_humidity if humidity is None else humidity

        if temperature is None or wind_speed is None:
            continue
        if 45.0 <= temperature <= 75.0 and 25.0 <= effective_humidity <= 60.0 and 3.0 <= wind_speed <= 15.0:
            return forecast_date.isoformat()

    return None


def _coerce_forecast_temperature(period: dict[str, Any]) -> float | None:
    """Normalize a forecast period temperature into Fahrenheit."""

    temperature = _coerce_float(period.get("temperature"))
    if temperature is None:
        return None

    temperature_unit = period.get("temperature_unit")
    if isinstance(temperature_unit, str) and temperature_unit.upper() == "C":
        return (temperature * 9.0 / 5.0) + 32.0
    return temperature


def _coerce_float(value: Any) -> float | None:
    """Convert numeric-like values into floats when possible."""

    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
