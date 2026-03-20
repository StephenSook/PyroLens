"""Net-positive metrics endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.net_positive_metric import NetPositiveMetricsResponse
from app.services.metrics_service import get_or_create_net_positive_metrics

logger = logging.getLogger(__name__)

router = APIRouter(tags=["metrics"])


@router.get("/api/metrics/net-positive", response_model=NetPositiveMetricsResponse)
async def get_net_positive_metrics(
    burn_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
) -> NetPositiveMetricsResponse:
    """Return cached or newly computed net-positive metrics for a burn."""

    try:
        return await get_or_create_net_positive_metrics(db, burn_id=burn_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unexpected net-positive metrics failure burn_id=%s", burn_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Net positive metrics request failed",
        ) from exc
