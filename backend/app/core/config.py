"""Application settings loaded from environment variables."""

from dataclasses import dataclass
from os import getenv

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str = getenv("APP_NAME", "PyroLens Backend")
    app_env: str = getenv("APP_ENV", "development")
    database_url: str = getenv(
        "DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/pyrolens"
    )
    log_level: str = getenv("LOG_LEVEL", "INFO")


settings = Settings()
