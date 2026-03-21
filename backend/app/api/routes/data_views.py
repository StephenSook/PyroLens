"""API routes for burn history, satellite NDVI, and active fire views."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.schemas import ActiveFiresResponse, FireDetection, NDVIPoint, NDVIResponse
from app.services import firms_client, sentinel_client
from app.services import burn_data_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Data & Satellite"])


@router.get("/burns/history", summary="Get historical prescribed burn records")
def get_burn_history_view(
    county: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return PostgreSQL-backed prescribed burn history as a GeoJSON-style feature collection."""

    # Validate optional date filters before delegating to the service layer.
    if from_date is not None and to_date is not None and from_date > to_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="from_date must be on or before to_date",
        )

    # Delegate burn-history retrieval to the database service.
    return burn_data_service.get_burn_history(db, county=county, from_date=from_date, to_date=to_date)


@router.get(
    "/satellite/ndvi",
    response_model=NDVIResponse,
    summary="Get Sentinel Hub NDVI time series",
)
async def get_ndvi_view(
    lat: float = Query(...),
    lon: float = Query(...),
    start_date: date = Query(...),
    end_date: date = Query(...),
    buffer_meters: int = Query(default=100),
) -> NDVIResponse:
    """Return an NDVI time series for a point and date window using Sentinel Hub."""

    # Validate coordinates, date order, and request window before calling Sentinel Hub.
    _validate_latitude(lat)
    _validate_longitude(lon)
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start_date must be on or before end_date",
        )
    if buffer_meters < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="buffer_meters must be at least 1",
        )

    # Call the Sentinel service client and normalize upstream failures for the API contract.
    try:
        raw_series = await sentinel_client.get_ndvi_timeseries(
            lat=lat,
            lon=lon,
            start_date=start_date,
            end_date=end_date,
            buffer_meters=buffer_meters,
        )
    except HTTPException as exc:
        raise _translate_sentinel_error(exc, lat=lat, lon=lon, start_date=start_date, end_date=end_date) from exc
    except Exception as exc:
        logger.exception(
            "Unexpected Sentinel NDVI failure lat=%s lon=%s start_date=%s end_date=%s",
            lat,
            lon,
            start_date,
            end_date,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Sentinel Hub NDVI data is temporarily unavailable",
        ) from exc

    # Filter the raw series into the response model without crashing on malformed points.
    series = _normalize_ndvi_series(raw_series)

    # Return a chart-friendly normalized response, including an empty series when no data exists.
    return NDVIResponse(
        lat=lat,
        lon=lon,
        start_date=start_date,
        end_date=end_date,
        buffer_meters=buffer_meters,
        series=series,
    )


@router.get(
    "/fires/active",
    response_model=ActiveFiresResponse,
    summary="Get active fire detections from NASA FIRMS",
)
async def get_active_fires_view(
    min_lat: float = Query(...),
    min_lon: float = Query(...),
    max_lat: float = Query(...),
    max_lon: float = Query(...),
    day_range: int = Query(default=3),
    source: str = Query(default="VIIRS_SNPP_NRT"),
) -> ActiveFiresResponse:
    """Return active fire detections for a bounding box using NASA FIRMS."""

    # Validate coordinate ranges and bounding-box ordering before formatting the FIRMS request.
    _validate_latitude(min_lat)
    _validate_longitude(min_lon)
    _validate_latitude(max_lat)
    _validate_longitude(max_lon)
    if min_lat >= max_lat:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="min_lat must be less than max_lat",
        )
    if min_lon >= max_lon:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="min_lon must be less than max_lon",
        )

    # Build the bbox string with the FIRMS client helper to keep formatting consistent.
    try:
        bbox = firms_client.format_bbox(min_lat=min_lat, min_lon=min_lon, max_lat=max_lat, max_lon=max_lon)
    except HTTPException as exc:
        raise _translate_validation_error(exc) from exc

    # Fetch active fires from NASA FIRMS and normalize upstream failures for callers.
    try:
        raw_fires = await firms_client.get_active_fires(bbox=bbox, day_range=day_range, source=source)
    except HTTPException as exc:
        raise _translate_firms_error(exc, bbox=bbox, day_range=day_range, source=source) from exc
    except Exception as exc:
        logger.exception("Unexpected FIRMS failure bbox=%s day_range=%s source=%s", bbox, day_range, source)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="NASA FIRMS active fire service is temporarily unavailable",
        ) from exc

    # Normalize the raw fire rows into a stable response model for frontend map rendering.
    fires = _normalize_fire_detections(raw_fires)
    return ActiveFiresResponse(
        bbox=bbox,
        day_range=day_range,
        source=source,
        count=len(fires),
        fires=fires,
    )


# Convert raw NDVI points into the public response schema.
def _normalize_ndvi_series(raw_series: list[dict[str, Any]]) -> list[NDVIPoint]:
    points: list[NDVIPoint] = []
    for point in raw_series:
        timestamp = point.get("timestamp")
        ndvi = point.get("ndvi")
        if timestamp is None or ndvi is None:
            continue
        try:
            points.append(NDVIPoint(timestamp=str(timestamp), ndvi=float(ndvi)))
        except (TypeError, ValueError):
            logger.debug("Skipping malformed NDVI point payload=%s", point)
    return points


# Convert raw FIRMS rows into typed fire-detection models.
def _normalize_fire_detections(raw_fires: list[dict[str, Any]]) -> list[FireDetection]:
    detections: list[FireDetection] = []
    for fire in raw_fires:
        latitude = _coerce_float(fire.get("latitude"))
        longitude = _coerce_float(fire.get("longitude"))
        if latitude is None or longitude is None:
            logger.debug("Skipping FIRMS row with invalid coordinates payload=%s", fire)
            continue
        detections.append(
            FireDetection(
                latitude=latitude,
                longitude=longitude,
                frp=_coerce_float(fire.get("frp")),
                confidence=_coerce_str(fire.get("confidence")),
                acq_date=_coerce_str(fire.get("acq_date")),
                acq_time=_coerce_str(fire.get("acq_time")),
                satellite=_coerce_str(fire.get("satellite")),
            )
        )
    return detections


# Validate latitude values with API-friendly 422 errors.
def _validate_latitude(value: float) -> None:
    if not (-90 <= value <= 90):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Latitude must be between -90 and 90",
        )


# Validate longitude values with API-friendly 422 errors.
def _validate_longitude(value: float) -> None:
    if not (-180 <= value <= 180):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Longitude must be between -180 and 180",
        )


# Normalize validation errors from service helpers into HTTP 422 responses.
def _translate_validation_error(exc: HTTPException) -> HTTPException:
    detail = str(exc.detail)
    if exc.status_code == status.HTTP_400_BAD_REQUEST:
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
        )
    return exc


# Translate Sentinel Hub failures into user-facing API responses.
def _translate_sentinel_error(
    exc: HTTPException,
    *,
    lat: float,
    lon: float,
    start_date: date,
    end_date: date,
) -> HTTPException:
    detail = str(exc.detail)
    lowered_detail = detail.lower()

    if exc.status_code in {status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY}:
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
        )

    if any(
        token in lowered_detail
        for token in ("authentication", "credential", "unauthorized", "sentinel_client_id", "sentinel_client_secret")
    ):
        logger.warning(
            "Sentinel authentication failure lat=%s lon=%s start_date=%s end_date=%s detail=%s",
            lat,
            lon,
            start_date,
            end_date,
            detail,
        )
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sentinel Hub authentication is unavailable",
        )

    logger.warning(
        "Sentinel NDVI upstream failure lat=%s lon=%s start_date=%s end_date=%s status=%s detail=%s",
        lat,
        lon,
        start_date,
        end_date,
        exc.status_code,
        detail,
    )
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Sentinel Hub NDVI data is temporarily unavailable",
    )


# Translate FIRMS failures into map-friendly API responses.
def _translate_firms_error(
    exc: HTTPException,
    *,
    bbox: str,
    day_range: int,
    source: str,
) -> HTTPException:
    detail = str(exc.detail)
    lowered_detail = detail.lower()

    if exc.status_code in {status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY}:
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
        )

    if exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR:
        logger.warning("FIRMS configuration issue bbox=%s day_range=%s source=%s detail=%s", bbox, day_range, source, detail)
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="NASA FIRMS is not configured for this environment",
        )

    if exc.status_code == status.HTTP_503_SERVICE_UNAVAILABLE or any(
        token in lowered_detail for token in ("timed out", "request failed", "temporarily unavailable")
    ):
        logger.warning("FIRMS unreachable bbox=%s day_range=%s source=%s detail=%s", bbox, day_range, source, detail)
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="NASA FIRMS active fire service is temporarily unavailable",
        )

    logger.warning(
        "FIRMS upstream failure bbox=%s day_range=%s source=%s status=%s detail=%s",
        bbox,
        day_range,
        source,
        exc.status_code,
        detail,
    )
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="NASA FIRMS active fire lookup failed",
    )


# Coerce optional values into floats without raising.
def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# Coerce optional values into trimmed strings without raising.
def _coerce_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
