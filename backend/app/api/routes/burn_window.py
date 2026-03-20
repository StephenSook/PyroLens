"""Burn-window prediction endpoints."""

from fastapi import APIRouter

from app.ml.model import burn_window_model
from app.schemas.burn_window import BurnWindowRequest, BurnWindowResponse

router = APIRouter(prefix="/burn-window", tags=["burn-window"])


@router.post("/predict", response_model=BurnWindowResponse)
def predict_burn_window(features: BurnWindowRequest) -> BurnWindowResponse:
    """Predict burn-window success from a direct ML feature payload."""

    prediction = burn_window_model.predict(features)
    return BurnWindowResponse(**prediction)
