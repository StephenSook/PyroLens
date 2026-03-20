"""Route modules."""

from app.api.routes.burn_window import router as burn_window_router
from app.api.routes.data_views import router as data_views_router
from app.api.routes.health import router as health_router
from app.api.routes.sensors import router as sensors_router

__all__ = ["burn_window_router", "data_views_router", "health_router", "sensors_router"]
