"""Async NOAA weather client."""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx
from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = httpx.Timeout(15.0, connect=10.0)
DEFAULT_HEADERS = {
    "Accept": "application/geo+json",
    "User-Agent": f"{settings.APP_NAME} weather client",
}
MPH_PER_KPH = 0.621371
MPH_PER_MPS = 2.23694


async def get_current_and_forecast(lat: float, lon: float) -> dict[str, Any]:
    """Fetch current NOAA observations and the seven-day forecast for a point."""

    _validate_coordinates(lat=lat, lon=lon)
    points_url = f"{settings.NOAA_BASE_URL.rstrip('/')}/points/{lat},{lon}"

    async with httpx.AsyncClient(
        timeout=DEFAULT_TIMEOUT,
        headers=DEFAULT_HEADERS,
        trust_env=False,
    ) as client:
        points_data = await _get_json(
            client=client,
            url=points_url,
            error_context="NOAA point lookup",
            lat=lat,
            lon=lon,
        )
        properties = _require_mapping(points_data.get("properties"), "NOAA point lookup properties")
        forecast_url = _require_string(properties.get("forecast"), "NOAA forecast URL")
        stations_url = _require_string(properties.get("observationStations"), "NOAA observation stations URL")

        forecast_data = await _get_json(
            client=client,
            url=forecast_url,
            error_context="NOAA forecast lookup",
            lat=lat,
            lon=lon,
        )
        stations_data = await _get_json(
            client=client,
            url=stations_url,
            error_context="NOAA observation stations lookup",
            lat=lat,
            lon=lon,
        )

        current_conditions = await _get_current_conditions(
            client=client,
            stations_data=stations_data,
            lat=lat,
            lon=lon,
        )

    forecast_periods = _extract_forecast_periods(forecast_data)

    return {
        "temperature": current_conditions["temperature"],
        "humidity": current_conditions["humidity"],
        "wind_speed": current_conditions["wind_speed"],
        "wind_direction": current_conditions["wind_direction"],
        "forecast_periods": forecast_periods,
    }


async def _get_json(
    client: httpx.AsyncClient,
    url: str,
    error_context: str,
    lat: float,
    lon: float,
) -> dict[str, Any]:
    """Execute a NOAA request and return the parsed JSON body."""

    try:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()
    except httpx.TimeoutException as exc:
        logger.exception("%s timed out for lat=%s lon=%s url=%s", error_context, lat, lon, url)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{error_context} timed out",
        ) from exc
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        logger.warning(
            "%s failed for lat=%s lon=%s url=%s upstream_status=%s",
            error_context,
            lat,
            lon,
            url,
            status_code,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{error_context} failed with upstream status {status_code}",
        ) from exc
    except httpx.RequestError as exc:
        logger.exception("%s request error for lat=%s lon=%s url=%s", error_context, lat, lon, url)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{error_context} request failed",
        ) from exc
    except ValueError as exc:
        logger.exception("%s returned invalid JSON for lat=%s lon=%s url=%s", error_context, lat, lon, url)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{error_context} returned invalid JSON",
        ) from exc

    if not isinstance(data, dict):
        logger.error("%s returned unexpected JSON shape for lat=%s lon=%s url=%s", error_context, lat, lon, url)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{error_context} returned an unexpected payload",
        )

    return data


def _validate_coordinates(*, lat: float, lon: float) -> None:
    """Reject invalid coordinates before calling NOAA."""

    if not (-90 <= lat <= 90):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Latitude must be between -90 and 90",
        )
    if not (-180 <= lon <= 180):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Longitude must be between -180 and 180",
        )


async def _get_current_conditions(
    client: httpx.AsyncClient,
    stations_data: dict[str, Any],
    lat: float,
    lon: float,
) -> dict[str, float | str]:
    """Fetch current conditions from the closest station with complete data."""

    for station_url in _extract_station_urls(stations_data):
        latest_observation_url = f"{station_url.rstrip('/')}/observations/latest"
        latest_observation = await _get_json(
            client=client,
            url=latest_observation_url,
            error_context="NOAA latest observation lookup",
            lat=lat,
            lon=lon,
        )
        try:
            return _extract_current_conditions(latest_observation)
        except HTTPException as exc:
            logger.info(
                "Skipping NOAA station without complete conditions lat=%s lon=%s station_url=%s detail=%s",
                lat,
                lon,
                station_url,
                exc.detail,
            )

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="NOAA observation stations did not return complete current conditions",
    )


def _extract_station_urls(stations_data: dict[str, Any]) -> list[str]:
    """Get nearby station URLs from a NOAA station collection."""

    features = stations_data.get("features")
    if not isinstance(features, list) or not features:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="NOAA observation stations response did not include any stations",
        )

    station_urls: list[str] = []
    for feature in features:
        feature_data = _require_mapping(feature, "NOAA station feature")
        station_url = feature_data.get("id")
        if not isinstance(station_url, str) or not station_url:
            properties = _require_mapping(feature_data.get("properties"), "NOAA station properties")
            station_url = properties.get("@id")
        station_urls.append(_require_string(station_url, "NOAA station URL"))

    return station_urls


def _extract_current_conditions(observation_data: dict[str, Any]) -> dict[str, float | str]:
    """Normalize latest observation data into simple current conditions."""

    properties = _require_mapping(observation_data.get("properties"), "NOAA observation properties")
    temperature_f = _convert_temperature_to_fahrenheit(properties.get("temperature"))
    humidity = _extract_quantitative_value(properties.get("relativeHumidity"), "NOAA relative humidity")
    wind_speed_mph = _convert_speed_to_mph(properties.get("windSpeed"))
    wind_direction = _format_wind_direction(properties.get("windDirection"))

    return {
        "temperature": temperature_f,
        "humidity": humidity,
        "wind_speed": wind_speed_mph,
        "wind_direction": wind_direction,
    }


def _extract_forecast_periods(forecast_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize NOAA forecast periods into a smaller JSON-friendly structure."""

    properties = _require_mapping(forecast_data.get("properties"), "NOAA forecast properties")
    periods = properties.get("periods")
    if not isinstance(periods, list) or not periods:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="NOAA forecast response did not include any forecast periods",
        )

    simplified_periods: list[dict[str, Any]] = []
    for period in periods:
        period_data = _require_mapping(period, "NOAA forecast period")
        simplified_periods.append(
            {
                "name": _require_string(period_data.get("name"), "NOAA forecast period name"),
                "start_time": _require_string(period_data.get("startTime"), "NOAA forecast period start time"),
                "end_time": _require_string(period_data.get("endTime"), "NOAA forecast period end time"),
                "is_daytime": bool(period_data.get("isDaytime")),
                "temperature": float(_require_number(period_data.get("temperature"), "NOAA forecast period temperature")),
                "temperature_unit": _require_string(
                    period_data.get("temperatureUnit"),
                    "NOAA forecast period temperature unit",
                ),
                "wind_speed": _parse_forecast_wind_speed(period_data.get("windSpeed")),
                "wind_direction": _require_string(
                    period_data.get("windDirection"),
                    "NOAA forecast period wind direction",
                ),
                "precipitation_chance": _extract_optional_quantitative_value(
                    period_data.get("probabilityOfPrecipitation")
                ),
                "short_forecast": _require_string(
                    period_data.get("shortForecast"),
                    "NOAA forecast period short forecast",
                ),
                "detailed_forecast": _require_string(
                    period_data.get("detailedForecast"),
                    "NOAA forecast period detailed forecast",
                ),
            }
        )

    return simplified_periods


def _convert_temperature_to_fahrenheit(value: Any) -> float:
    """Convert a NOAA QuantitativeValue temperature to Fahrenheit."""

    quantitative_value = _extract_quantitative_value(value, "NOAA temperature")
    unit_code = _extract_unit_code(value)

    if unit_code.endswith("degF"):
        return quantitative_value
    if unit_code.endswith("degC"):
        return (quantitative_value * 9 / 5) + 32

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"NOAA temperature used unsupported unit {unit_code}",
    )


def _convert_speed_to_mph(value: Any) -> float:
    """Convert a NOAA QuantitativeValue speed to miles per hour."""

    quantitative_value = _extract_quantitative_value(value, "NOAA wind speed")
    unit_code = _extract_unit_code(value)

    if unit_code.endswith("km_h-1"):
        return quantitative_value * MPH_PER_KPH
    if unit_code.endswith("m_s-1"):
        return quantitative_value * MPH_PER_MPS
    if unit_code.endswith("mi_h-1"):
        return quantitative_value

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"NOAA wind speed used unsupported unit {unit_code}",
    )


def _format_wind_direction(value: Any) -> str:
    """Convert NOAA wind direction degrees to a cardinal direction."""

    degrees = _extract_quantitative_value(value, "NOAA wind direction")
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return directions[round(degrees / 45) % len(directions)]


def _parse_forecast_wind_speed(value: Any) -> float:
    """Extract a representative mph value from NOAA forecast wind speed text."""

    if not isinstance(value, str) or not value.strip():
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="NOAA forecast period did not include a valid wind speed",
        )

    matches = [float(match) for match in re.findall(r"\d+(?:\.\d+)?", value)]
    if not matches:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="NOAA forecast wind speed could not be parsed",
        )

    return max(matches)


def _extract_quantitative_value(value: Any, field_name: str) -> float:
    """Extract a numeric value from NOAA QuantitativeValue payloads."""

    extracted = _extract_optional_quantitative_value(value)
    if extracted is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{field_name} was missing from the NOAA response",
        )
    return extracted


def _extract_optional_quantitative_value(value: Any) -> float | None:
    """Extract an optional numeric value from NOAA QuantitativeValue payloads."""

    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, dict):
        return None

    numeric_value = value.get("value")
    if numeric_value is None:
        return None
    if not isinstance(numeric_value, (int, float)):
        return None
    return float(numeric_value)


def _extract_unit_code(value: Any) -> str:
    """Read the NOAA unit code from a QuantitativeValue object."""

    if not isinstance(value, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="NOAA response used an unexpected unit payload",
        )

    return _require_string(value.get("unitCode"), "NOAA unit code")


def _require_mapping(value: Any, field_name: str) -> dict[str, Any]:
    """Ensure a value is a mapping."""

    if not isinstance(value, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{field_name} was missing from the NOAA response",
        )
    return value


def _require_string(value: Any, field_name: str) -> str:
    """Ensure a value is a non-empty string."""

    if not isinstance(value, str) or not value:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{field_name} was missing from the NOAA response",
        )
    return value


def _require_number(value: Any, field_name: str) -> float:
    """Ensure a value is numeric."""

    if not isinstance(value, (int, float)):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{field_name} was missing from the NOAA response",
        )
    return float(value)
