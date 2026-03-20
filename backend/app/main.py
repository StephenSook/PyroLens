"""FastAPI application entrypoint."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.core.config import settings
from app.ml.model import burn_window_model


logger = logging.getLogger(__name__)


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
    yield


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
