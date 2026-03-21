"""Application settings loaded from environment variables and .env."""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    APP_NAME: str = "PyroLens Backend"
    ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    MODEL_PATH: str = "models/burn_model.pkl"
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/pyrolens"
    DATABASE_SSLMODE: str | None = None
    DATABASE_DISABLE_POOLING: bool = False
    NOAA_BASE_URL: str = "https://api.weather.gov"
    FIRMS_BASE_URL: str = "https://firms.modaps.eosdis.nasa.gov"
    FIRMS_MAP_KEY: str | None = Field(default=None, validation_alias=AliasChoices("FIRMS_MAP_KEY", "MAP_KEY"))
    SENTINEL_BASE_URL: str = "https://services.sentinel-hub.com"
    SENTINEL_CLIENT_ID: str | None = None
    SENTINEL_CLIENT_SECRET: str | None = None
    WILDFIRE_BASELINE_EMISSIONS_PER_ACRE: float = 18.5
    PRESCRIBED_BURN_EMISSIONS_PER_ACRE: float = 6.25

    @field_validator("SENTINEL_BASE_URL", mode="before")
    @classmethod
    def normalize_sentinel_base_url(cls, value: str) -> str:
        """Normalize known Sentinel Hub base URL variants."""

        if isinstance(value, str) and value.rstrip("/") == "https://sentinel-hub.com":
            return "https://services.sentinel-hub.com"
        return value

    @property
    def database_url_with_options(self) -> str:
        """Return the database URL with any required SSL options applied."""

        sslmode = self.DATABASE_SSLMODE or ("require" if self._is_supabase_database_url(self.DATABASE_URL) else None)
        if not sslmode:
            return self.DATABASE_URL

        return self._set_database_query_param(self.DATABASE_URL, "sslmode", sslmode)

    @property
    def database_use_null_pool(self) -> bool:
        """Return whether SQLAlchemy should disable app-level pooling."""

        if self.DATABASE_DISABLE_POOLING:
            return True

        database_url = self.DATABASE_URL.lower()
        return "pooler.supabase.com:6543" in database_url

    @staticmethod
    def _is_supabase_database_url(database_url: str) -> bool:
        normalized_url = database_url.lower()
        return "supabase.co" in normalized_url or "pooler.supabase.com" in normalized_url

    @staticmethod
    def _set_database_query_param(database_url: str, key: str, value: str) -> str:
        parsed_url = urlsplit(database_url)
        query_params = dict(parse_qsl(parsed_url.query, keep_blank_values=True))
        query_params[key] = value
        return urlunsplit(parsed_url._replace(query=urlencode(query_params)))


settings = Settings()
