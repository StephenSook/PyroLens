"""Application settings loaded from environment variables and .env."""

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    APP_NAME: str = "PyroLens Backend"
    ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    MODEL_PATH: str = "models/burn_model.pkl"
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/pyrolens"
    NOAA_BASE_URL: str = "https://api.weather.gov"
    FIRMS_BASE_URL: str = "https://firms.modaps.eosdis.nasa.gov"
    FIRMS_MAP_KEY: str | None = Field(default=None, validation_alias=AliasChoices("FIRMS_MAP_KEY", "MAP_KEY"))
    SENTINEL_BASE_URL: str = "https://services.sentinel-hub.com"
    SENTINEL_CLIENT_ID: str | None = None
    SENTINEL_CLIENT_SECRET: str | None = None

    @field_validator("SENTINEL_BASE_URL", mode="before")
    @classmethod
    def normalize_sentinel_base_url(cls, value: str) -> str:
        """Normalize known Sentinel Hub base URL variants."""

        if isinstance(value, str) and value.rstrip("/") == "https://sentinel-hub.com":
            return "https://services.sentinel-hub.com"
        return value


settings = Settings()
