"""FastAPI application entrypoint."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.routes import burn_window_router, data_views_router, health_router, metrics_router, sensors_router
from app.core.config import settings
from app.db.session import engine
from app.ml.model import burn_window_model


logger = logging.getLogger(__name__)
OPENAPI_TAGS = [
    {"name": "Burn Window", "description": "Burn-window prediction and recommendation endpoints."},
    {"name": "Sensors", "description": "Sensor ingestion and related background prediction hooks."},
    {"name": "Data & Satellite", "description": "Historical burn data and satellite-derived vegetation endpoints."},
    {"name": "Net Positive Metrics", "description": "Burn impact metrics and net-positive emissions outcomes."},
    {"name": "Health", "description": "Operational health checks."},
]


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Load shared application resources once for the process lifespan."""

    burn_window_model.load_model(settings.MODEL_PATH)
    if burn_window_model.using_placeholder:
        logger.warning(
            "Burn-window model placeholder is active model_path=%s",
            burn_window_model.loaded_path or settings.MODEL_PATH,
        )
    else:
        logger.info(
            "Burn-window model loaded model_path=%s backend=%s",
            burn_window_model.loaded_path or settings.MODEL_PATH,
            burn_window_model.model_backend,
        )
    _verify_database_connectivity()
    yield


def _verify_database_connectivity() -> None:
    """Log whether the application can reach the configured database."""

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        logger.info("Database connectivity check succeeded")
    except Exception:
        logger.exception("Database connectivity check failed")


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan, openapi_tags=OPENAPI_TAGS)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(burn_window_router, prefix="/api")
app.include_router(sensors_router, prefix="/api")
app.include_router(data_views_router, prefix="/api")
app.include_router(metrics_router, prefix="/api")
app.include_router(health_router, prefix="/api")
