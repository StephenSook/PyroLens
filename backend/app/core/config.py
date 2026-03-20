"""Application settings loaded from environment variables and .env."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    APP_NAME: str = "PyroLens Backend"
    ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/pyrolens"
    NOAA_BASE_URL: str = "https://api.weather.gov"
    FIRMS_BASE_URL: str = "https://firms.modaps.eosdis.nasa.gov"
    SENTINEL_BASE_URL: str = "https://services.sentinel-hub.com"


settings = Settings()
