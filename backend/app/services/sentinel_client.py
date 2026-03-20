"""Async Sentinel Hub client for OAuth and NDVI retrieval."""

from __future__ import annotations

import asyncio
import logging
import math
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

import httpx
from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
DEFAULT_HEADERS = {
    "Accept": "application/json",
    "User-Agent": f"{settings.APP_NAME} Sentinel client",
}
TOKEN_ENDPOINT = "https://services.sentinel-hub.com/auth/realms/main/protocol/openid-connect/token"
TOKEN_REFRESH_BUFFER_SECONDS = 60
NDVI_EVALSCRIPT = """
//VERSION=3
function setup() {
  return {
    input: [{
      bands: ["B04", "B08", "dataMask"],
      units: "REFLECTANCE"
    }],
    output: [
      {
        id: "ndvi",
        bands: 1,
        sampleType: "FLOAT32"
      },
      {
        id: "dataMask",
        bands: 1
      }
    ]
  };
}

function evaluatePixel(sample) {
  const denominator = sample.B08 + sample.B04;
  const isValid = sample.dataMask === 1 && denominator !== 0;
  const ndvi = isValid ? (sample.B08 - sample.B04) / denominator : 0;

  return {
    ndvi: [ndvi],
    dataMask: [isValid ? 1 : 0]
  };
}
""".strip()

_TOKEN_CACHE: dict[str, Any] = {"access_token": None, "expires_at": None}
_TOKEN_LOCK = asyncio.Lock()


async def get_access_token() -> str:
    """Return a cached Sentinel Hub access token or fetch a new one."""

    cached_token = _get_cached_access_token()
    if cached_token:
        return cached_token

    async with _TOKEN_LOCK:
        cached_token = _get_cached_access_token()
        if cached_token:
            return cached_token

        client_id, client_secret = _require_credentials()
        token_payload = await _request_access_token(client_id=client_id, client_secret=client_secret)
        access_token = _require_string(token_payload.get("access_token"), "Sentinel Hub access token")
        expires_at = _resolve_expiration(token_payload)

        _TOKEN_CACHE["access_token"] = access_token
        _TOKEN_CACHE["expires_at"] = expires_at
        return access_token


async def get_ndvi_timeseries(
    lat: float,
    lon: float,
    start_date: date,
    end_date: date,
    buffer_meters: int = 100,
) -> list[dict[str, Any]]:
    """Fetch a normalized NDVI time series for a small area around a point."""

    _validate_coordinates(lat=lat, lon=lon)
    _validate_date_range(start_date=start_date, end_date=end_date)
    _validate_buffer_meters(buffer_meters)

    access_token = await get_access_token()
    bbox = _build_bbox(lat=lat, lon=lon, buffer_meters=buffer_meters)
    payload = _build_statistics_payload(
        bbox=bbox,
        lat=lat,
        start_date=start_date,
        end_date=end_date,
    )

    stats_response = await _post_statistics_request(payload=payload, access_token=access_token, lat=lat, lon=lon)
    return _parse_ndvi_timeseries(stats_response, lat=lat, lon=lon)


async def get_latest_ndvi(lat: float, lon: float, lookback_days: int = 30) -> float | None:
    """Return the most recent available NDVI value or ``None``."""

    if lookback_days < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="lookback_days must be at least 1",
        )

    end_date = date.today()
    start_date = end_date - timedelta(days=lookback_days)
    series = await get_ndvi_timeseries(
        lat=lat,
        lon=lon,
        start_date=start_date,
        end_date=end_date,
    )
    if not series:
        return None
    return float(series[-1]["ndvi"])


def _get_cached_access_token() -> str | None:
    """Return the in-memory token if it is still valid."""

    access_token = _TOKEN_CACHE.get("access_token")
    expires_at = _TOKEN_CACHE.get("expires_at")
    if not isinstance(access_token, str) or not access_token:
        return None
    if not isinstance(expires_at, datetime):
        return None
    if expires_at <= datetime.now(timezone.utc):
        return None
    return access_token


def _require_credentials() -> tuple[str, str]:
    """Return Sentinel Hub credentials or raise a configuration error."""

    if not settings.SENTINEL_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SENTINEL_CLIENT_ID is not configured",
        )
    if not settings.SENTINEL_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SENTINEL_CLIENT_SECRET is not configured",
        )
    return settings.SENTINEL_CLIENT_ID, settings.SENTINEL_CLIENT_SECRET


async def _request_access_token(client_id: str, client_secret: str) -> dict[str, Any]:
    """Request a fresh Sentinel Hub OAuth token."""

    async with httpx.AsyncClient(
        timeout=DEFAULT_TIMEOUT,
        headers={
            **DEFAULT_HEADERS,
            "Content-Type": "application/x-www-form-urlencoded",
        },
        trust_env=False,
    ) as client:
        try:
            response = await client.post(
                TOKEN_ENDPOINT,
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
            )
            response.raise_for_status()
            data = response.json()
        except httpx.TimeoutException as exc:
            logger.exception("Sentinel Hub token request timed out")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Sentinel Hub authentication timed out",
            ) from exc
        except httpx.HTTPStatusError as exc:
            upstream_status = exc.response.status_code
            logger.warning("Sentinel Hub token request failed upstream_status=%s", upstream_status)
            detail = "Sentinel Hub authentication failed"
            if upstream_status in {400, 401, 403}:
                detail = "Sentinel Hub credentials are invalid or unauthorized"
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=detail,
            ) from exc
        except httpx.RequestError as exc:
            logger.exception("Sentinel Hub token request error")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Sentinel Hub authentication request failed",
            ) from exc
        except ValueError as exc:
            logger.exception("Sentinel Hub token response was not valid JSON")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Sentinel Hub authentication returned invalid JSON",
            ) from exc

    if not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Sentinel Hub authentication returned an unexpected payload",
        )
    return data


def _resolve_expiration(token_payload: dict[str, Any]) -> datetime:
    """Compute the cache expiration time for an OAuth token response."""

    now = datetime.now(timezone.utc)
    expires_in = token_payload.get("expires_in")
    if isinstance(expires_in, (int, float)):
        ttl_seconds = max(int(expires_in) - TOKEN_REFRESH_BUFFER_SECONDS, 1)
        return now + timedelta(seconds=ttl_seconds)

    exp = token_payload.get("exp")
    if isinstance(exp, (int, float)):
        expiration = datetime.fromtimestamp(float(exp), tz=timezone.utc)
        buffered_expiration = expiration - timedelta(seconds=TOKEN_REFRESH_BUFFER_SECONDS)
        return _max_datetime(now + timedelta(seconds=1), buffered_expiration)

    return now + timedelta(minutes=50)


def _build_bbox(lat: float, lon: float, buffer_meters: int) -> list[float]:
    """Build a small CRS84 bbox around a point."""

    lat_delta = buffer_meters / 111_320
    lon_scale = math.cos(math.radians(lat))
    lon_delta = buffer_meters / max(111_320 * max(abs(lon_scale), 1e-6), 1e-6)

    south = max(lat - lat_delta, -90.0)
    north = min(lat + lat_delta, 90.0)
    west = max(lon - lon_delta, -180.0)
    east = min(lon + lon_delta, 180.0)

    return [west, south, east, north]


def _build_statistics_payload(
    bbox: list[float],
    lat: float,
    start_date: date,
    end_date: date,
) -> dict[str, Any]:
    """Create a Statistical API payload for NDVI over Sentinel-2 L2A."""

    resx, resy = _build_degree_resolution(lat=lat)

    return {
        "input": {
            "bounds": {
                "bbox": bbox,
                "properties": {
                    "crs": "http://www.opengis.net/def/crs/OGC/1.3/CRS84",
                },
            },
            "data": [
                {
                    "type": "sentinel-2-l2a",
                    "dataFilter": {
                        "mosaickingOrder": "leastCC",
                    },
                    "processing": {
                        "harmonizeValues": "true",
                    },
                }
            ],
        },
        "aggregation": {
            "timeRange": {
                "from": _format_start_datetime(start_date),
                "to": _format_end_datetime(end_date),
            },
            "aggregationInterval": {
                "of": "P1D",
            },
            "evalscript": NDVI_EVALSCRIPT,
            "resx": resx,
            "resy": resy,
        },
    }


def _build_degree_resolution(lat: float) -> tuple[float, float]:
    """Approximate a 10-meter resolution in degrees for the request grid."""

    lat_resolution = 10 / 111_320
    lon_scale = math.cos(math.radians(lat))
    lon_resolution = 10 / max(111_320 * max(abs(lon_scale), 1e-6), 1e-6)
    return lon_resolution, lat_resolution


async def _post_statistics_request(
    payload: dict[str, Any],
    access_token: str,
    lat: float,
    lon: float,
) -> dict[str, Any]:
    """Submit an NDVI statistics request to Sentinel Hub."""

    url = f"{settings.SENTINEL_BASE_URL.rstrip('/')}/api/v1/statistics"

    async with httpx.AsyncClient(
        timeout=DEFAULT_TIMEOUT,
        headers={
            **DEFAULT_HEADERS,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        trust_env=False,
    ) as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
        except httpx.TimeoutException as exc:
            logger.exception("Sentinel NDVI request timed out lat=%s lon=%s", lat, lon)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Sentinel Hub NDVI lookup timed out",
            ) from exc
        except httpx.HTTPStatusError as exc:
            upstream_status = exc.response.status_code
            logger.warning(
                "Sentinel NDVI request failed lat=%s lon=%s upstream_status=%s",
                lat,
                lon,
                upstream_status,
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Sentinel Hub NDVI lookup failed with upstream status {upstream_status}",
            ) from exc
        except httpx.RequestError as exc:
            logger.exception("Sentinel NDVI request error lat=%s lon=%s", lat, lon)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Sentinel Hub NDVI lookup request failed",
            ) from exc
        except ValueError as exc:
            logger.exception("Sentinel NDVI response was not valid JSON lat=%s lon=%s", lat, lon)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Sentinel Hub NDVI lookup returned invalid JSON",
            ) from exc

    if not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Sentinel Hub NDVI lookup returned an unexpected payload",
        )
    return data


def _parse_ndvi_timeseries(response_data: dict[str, Any], lat: float, lon: float) -> list[dict[str, Any]]:
    """Parse Statistical API output into a normalized NDVI time series."""

    data_items = response_data.get("data")
    if not isinstance(data_items, list):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Sentinel Hub NDVI lookup returned an unexpected payload",
        )

    timeseries: list[dict[str, Any]] = []
    for item in data_items:
        if not isinstance(item, dict):
            continue

        timestamp = _extract_interval_date(item)
        ndvi = _extract_mean_ndvi(item)
        if timestamp is None or ndvi is None:
            continue

        timeseries.append(
            {
                "timestamp": timestamp,
                "ndvi": round(ndvi, 4),
            }
        )

    logger.info("Sentinel NDVI lookup produced %s observations lat=%s lon=%s", len(timeseries), lat, lon)
    return timeseries


def _extract_interval_date(item: dict[str, Any]) -> str | None:
    """Extract the interval start date from a Statistical API bucket."""

    interval = item.get("interval")
    if not isinstance(interval, dict):
        return None

    from_timestamp = interval.get("from")
    if not isinstance(from_timestamp, str) or not from_timestamp:
        return None

    return from_timestamp.split("T", 1)[0]


def _extract_mean_ndvi(item: dict[str, Any]) -> float | None:
    """Extract the mean NDVI value from a Statistical API bucket."""

    outputs = item.get("outputs")
    if not isinstance(outputs, dict):
        return None

    ndvi_output = outputs.get("ndvi")
    if not isinstance(ndvi_output, dict):
        return None

    bands = ndvi_output.get("bands")
    if not isinstance(bands, dict):
        return None

    band_payload = bands.get("B0")
    if not isinstance(band_payload, dict):
        band_payload = next((value for value in bands.values() if isinstance(value, dict)), None)
    if not isinstance(band_payload, dict):
        return None

    stats_payload = band_payload.get("stats")
    if not isinstance(stats_payload, dict):
        return None

    sample_count = stats_payload.get("sampleCount")
    no_data_count = stats_payload.get("noDataCount")
    if isinstance(sample_count, (int, float)) and isinstance(no_data_count, (int, float)) and sample_count <= no_data_count:
        return None

    mean_ndvi = stats_payload.get("mean")
    if not isinstance(mean_ndvi, (int, float)):
        return None
    return float(mean_ndvi)


def _validate_coordinates(*, lat: float, lon: float) -> None:
    """Reject invalid coordinates before calling Sentinel Hub."""

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


def _validate_date_range(*, start_date: date, end_date: date) -> None:
    """Validate the requested NDVI date range."""

    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be on or before end_date",
        )


def _validate_buffer_meters(buffer_meters: int) -> None:
    """Validate the point-buffer size."""

    if buffer_meters < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="buffer_meters must be at least 1",
        )


def _format_start_datetime(value: date) -> str:
    """Convert a date into a Sentinel-compatible interval start."""

    return datetime.combine(value, time.min, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def _format_end_datetime(value: date) -> str:
    """Convert a date into a Sentinel-compatible inclusive interval end."""

    return datetime.combine(value + timedelta(days=1), time.min, tzinfo=timezone.utc).isoformat().replace(
        "+00:00",
        "Z",
    )


def _require_string(value: Any, field_name: str) -> str:
    """Ensure a value is a non-empty string."""

    if not isinstance(value, str) or not value:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{field_name} was missing from the Sentinel Hub response",
        )
    return value


def _max_datetime(first: datetime, second: datetime) -> datetime:
    """Return the later of two datetimes."""

    return first if first >= second else second
