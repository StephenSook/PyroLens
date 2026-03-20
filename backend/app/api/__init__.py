"""API package exposing application routers."""

from fastapi import APIRouter

from app.api.routes import health_router

api_router = APIRouter()
api_router.include_router(health_router)
