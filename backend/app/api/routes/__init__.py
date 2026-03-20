"""Route modules."""

from app.api.routes.burn_window import router as burn_window_router
from app.api.routes.health import router as health_router

__all__ = ["burn_window_router", "health_router"]
