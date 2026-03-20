"""Read-only data view endpoints."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.schemas import NDVIPoint, NDVIResponse
from app.services import sentinel_client
from app.services.burn_data_service import get_burn_history

logger = logging.getLogger(__name__)

router = APIRouter(tags=["data-views"])


@router.get("/api/burns/history")
def get_burn_history_view(
    county: str | None = None,
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return historical burn records as a GeoJSON FeatureCollection."""

    return get_burn_history(db, county=county, from_date=from_date, to_date=to_date)


@router.get("/api/satellite/ndvi", response_model=NDVIResponse)
async def get_ndvi_view(
    lat: float,
    lon: float,
    start_date: date,
    end_date: date,
) -> NDVIResponse:
    """Return NDVI time-series data and simple recovery metrics for a location."""

    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start_date must be before end_date",
        )

    try:
        series = await sentinel_client.get_ndvi_timeseries(
            lat=lat,
            lon=lon,
            start_date=start_date,
            end_date=end_date,
        )
    except HTTPException as exc:
        logger.warning(
            "NDVI request failed lat=%s lon=%s start_date=%s end_date=%s detail=%s",
            lat,
            lon,
            start_date,
            end_date,
            exc.detail,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="NDVI data unavailable for the requested location and date range",
        ) from exc
    except Exception as exc:
        logger.exception(
            "Unexpected NDVI request failure lat=%s lon=%s start_date=%s end_date=%s",
            lat,
            lon,
            start_date,
            end_date,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="NDVI data unavailable for the requested location and date range",
        ) from exc

    if not series:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="NDVI data unavailable for the requested location and date range",
        )

    points = [
        NDVIPoint(timestamp=str(point["timestamp"]), ndvi=float(point["ndvi"]))
        for point in series
        if point.get("timestamp") is not None and point.get("ndvi") is not None
    ]

    if not points:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="NDVI data unavailable for the requested location and date range",
        )

    peak_point = max(points, key=lambda point: point.ndvi)
    peak_ndvi = float(peak_point.ndvi)
    peak_date = _parse_point_date(peak_point.timestamp)
    recovery_months = 0 if peak_date is None else max(0, _month_delta(start_date, peak_date))

    return NDVIResponse(
        lat=lat,
        lon=lon,
        start_date=start_date,
        end_date=end_date,
        points=points,
        peak_ndvi=peak_ndvi,
        recovery_months=recovery_months,
    )


def _parse_point_date(timestamp: str) -> date | None:
    """Parse an NDVI timestamp string into a date when possible."""

    try:
        return date.fromisoformat(timestamp)
    except ValueError:
        return None


def _month_delta(start_date: date, end_date: date) -> int:
    """Compute whole-month distance between two dates."""

    return (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
