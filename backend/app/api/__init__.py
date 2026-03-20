"""API package exposing application routers."""

from fastapi import APIRouter

from app.api.routes import burn_window_router, data_views_router, health_router, metrics_router, sensors_router

api_router = APIRouter()
api_router.include_router(burn_window_router)
api_router.include_router(data_views_router)
api_router.include_router(health_router)
api_router.include_router(metrics_router)
api_router.include_router(sensors_router)
