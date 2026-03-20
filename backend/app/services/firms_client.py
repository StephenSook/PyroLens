"""Async NASA FIRMS client for active fire detections."""

from __future__ import annotations

import csv
import logging
from io import StringIO
from typing import Any

import httpx
from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = httpx.Timeout(20.0, connect=10.0)
DEFAULT_HEADERS = {
    "Accept": "text/csv",
    "User-Agent": f"{settings.APP_NAME} FIRMS client",
}
SUPPORTED_DAY_RANGE = range(1, 6)
FIRE_FIELD_ALIASES = {
    "latitude": ("latitude",),
    "longitude": ("longitude",),
    "brightness": ("brightness", "bright_ti4"),
    "scan": ("scan",),
    "track": ("track",),
    "acq_date": ("acq_date",),
    "acq_time": ("acq_time",),
    "satellite": ("satellite",),
    "confidence": ("confidence",),
    "version": ("version",),
    "bright_t31": ("bright_t31",),
    "frp": ("frp",),
    "daynight": ("daynight",),
}
FLOAT_FIELDS = {"latitude", "longitude", "brightness", "scan", "track", "bright_t31", "frp"}


def format_bbox(min_lat: float, min_lon: float, max_lat: float, max_lon: float) -> str:
    """Format a FIRMS bbox as ``west,south,east,north``."""

    _validate_coordinate(lat=min_lat, lon=min_lon)
    _validate_coordinate(lat=max_lat, lon=max_lon)

    if min_lat >= max_lat:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Minimum latitude must be less than maximum latitude",
        )
    if min_lon >= max_lon:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Minimum longitude must be less than maximum longitude",
        )

    return f"{min_lon},{min_lat},{max_lon},{max_lat}"


async def get_active_fires(
    bbox: str,
    day_range: int = 3,
    source: str = "VIIRS_SNPP_NRT",
) -> list[dict[str, Any]]:
    """Fetch active fire detections from NASA FIRMS for a bounding box."""

    firms_map_key = _require_map_key()
    normalized_bbox = _validate_bbox(bbox)
    _validate_day_range(day_range)
    _validate_source(source)

    url = (
        f"{settings.FIRMS_BASE_URL.rstrip('/')}/api/area/csv/"
        f"{firms_map_key}/{source}/{normalized_bbox}/{day_range}"
    )

    async with httpx.AsyncClient(
        timeout=DEFAULT_TIMEOUT,
        headers=DEFAULT_HEADERS,
        trust_env=False,
    ) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            logger.exception(
                "FIRMS request timed out bbox=%s day_range=%s source=%s url=%s",
                normalized_bbox,
                day_range,
                source,
                url,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="FIRMS active fire lookup timed out",
            ) from exc
        except httpx.HTTPStatusError as exc:
            upstream_status = exc.response.status_code
            logger.warning(
                "FIRMS request failed bbox=%s day_range=%s source=%s upstream_status=%s",
                normalized_bbox,
                day_range,
                source,
                upstream_status,
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"FIRMS active fire lookup failed with upstream status {upstream_status}",
            ) from exc
        except httpx.RequestError as exc:
            logger.exception(
                "FIRMS request error bbox=%s day_range=%s source=%s url=%s",
                normalized_bbox,
                day_range,
                source,
                url,
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="FIRMS active fire lookup request failed",
            ) from exc

    return _parse_fire_csv(
        csv_text=response.text,
        bbox=normalized_bbox,
        day_range=day_range,
        source=source,
    )


def _require_map_key() -> str:
    """Return the configured FIRMS map key or raise a configuration error."""

    if not settings.FIRMS_MAP_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="FIRMS_MAP_KEY is not configured",
        )
    return settings.FIRMS_MAP_KEY


def _validate_day_range(day_range: int) -> None:
    """Validate the FIRMS day-range constraint."""

    if day_range not in SUPPORTED_DAY_RANGE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="day_range must be between 1 and 5",
        )


def _validate_source(source: str) -> None:
    """Validate the FIRMS source input."""

    if not isinstance(source, str) or not source.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="source must be a non-empty FIRMS source identifier",
        )


def _validate_bbox(bbox: str) -> str:
    """Validate a FIRMS bbox string in ``west,south,east,north`` order."""

    if bbox == "world":
        return bbox
    if not isinstance(bbox, str) or not bbox.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="bbox must be a non-empty string in west,south,east,north format",
        )

    parts = [part.strip() for part in bbox.split(",")]
    if len(parts) != 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="bbox must contain four comma-separated coordinates in west,south,east,north order",
        )

    try:
        west, south, east, north = (float(part) for part in parts)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="bbox coordinates must be numeric values",
        ) from exc

    _validate_coordinate(lat=south, lon=west)
    _validate_coordinate(lat=north, lon=east)

    if west >= east:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="bbox west coordinate must be less than east coordinate",
        )
    if south >= north:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="bbox south coordinate must be less than north coordinate",
        )

    return f"{west},{south},{east},{north}"


def _validate_coordinate(*, lat: float, lon: float) -> None:
    """Reject invalid coordinates before calling FIRMS."""

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


def _parse_fire_csv(csv_text: str, bbox: str, day_range: int, source: str) -> list[dict[str, Any]]:
    """Parse a FIRMS CSV response into normalized fire-detection rows."""

    if not csv_text.strip():
        logger.info("FIRMS returned an empty CSV response bbox=%s day_range=%s source=%s", bbox, day_range, source)
        return []

    try:
        reader = csv.DictReader(StringIO(csv_text))
    except csv.Error as exc:
        logger.exception("FIRMS CSV parsing failed before reading rows bbox=%s source=%s", bbox, source)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="FIRMS active fire lookup returned malformed CSV",
        ) from exc

    if not reader.fieldnames:
        logger.warning("FIRMS CSV response had no header row bbox=%s source=%s", bbox, source)
        return []

    try:
        rows = [row for row in reader if row and any((value or "").strip() for value in row.values())]
    except csv.Error as exc:
        logger.exception("FIRMS CSV row parsing failed bbox=%s source=%s", bbox, source)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="FIRMS active fire lookup returned malformed CSV rows",
        ) from exc

    if not rows:
        logger.info("FIRMS returned no active fire detections bbox=%s day_range=%s source=%s", bbox, day_range, source)
        return []

    return [_normalize_fire_record(row) for row in rows]


def _normalize_fire_record(row: dict[str, str | None]) -> dict[str, Any]:
    """Normalize a FIRMS CSV row into a map-friendly fire-detection payload."""

    record: dict[str, Any] = {}

    for output_field, aliases in FIRE_FIELD_ALIASES.items():
        raw_value = next((row.get(alias) for alias in aliases if row.get(alias) not in (None, "")), None)
        normalized_value = _normalize_field(output_field, raw_value)
        if normalized_value is not None:
            record[output_field] = normalized_value

    return record


def _normalize_field(field_name: str, value: str | None) -> Any:
    """Normalize individual FIRMS CSV fields into typed Python values."""

    if value is None:
        return None

    trimmed = value.strip()
    if not trimmed:
        return None

    if field_name in FLOAT_FIELDS:
        try:
            return float(trimmed)
        except ValueError:
            logger.debug("FIRMS field %s could not be parsed as float: %s", field_name, trimmed)
            return trimmed

    if field_name == "acq_time":
        return trimmed.zfill(4)

    return trimmed
