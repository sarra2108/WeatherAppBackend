from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Weather App Backend"
    database_url: str = "sqlite:///./weather_app.db"
    nominatim_base_url: str = "https://nominatim.openstreetmap.org"
    open_meteo_base_url: str = "https://api.open-meteo.com/v1"
    open_meteo_archive_url: str = "https://archive-api.open-meteo.com/v1/archive"
    http_timeout_seconds: float = 12.0
    max_date_range_days: int = 31

    model_config = SettingsConfigDict(env_file=".env", env_prefix="WEATHER_")


@lru_cache
def get_settings() -> Settings:
    return Settings()
