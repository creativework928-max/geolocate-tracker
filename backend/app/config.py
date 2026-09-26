from __future__ import annotations

import json
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "GeoLocate Tracker"
    app_env: str = "development"
    debug: bool = False

    geoip_provider: str = "maxmind"
    geoip_account_id: str | None = None
    geoip_license_key: str | None = None
    geoip_service: str = "city"
    geoip_timeout_seconds: float = 5.0

    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600

    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 30

    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:8000"]
    )

    trusted_proxies: list[str] = Field(default_factory=list)

    log_level: str = "INFO"

    demo_mode: bool = False

    map_tile_url: str = (
        "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    )
    map_attribution: str = (
        '&copy; <a href="https://www.openstreetmap.org/copyright">'
        "OpenStreetMap</a> contributors"
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> list[str]:
        if isinstance(value, list):
            return value

        if isinstance(value, str):
            value = value.strip()

            if not value:
                return []

            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
            except json.JSONDecodeError:
                pass

            return [
                item.strip()
                for item in value.split(",")
                if item.strip()
            ]

        raise ValueError("CORS_ORIGINS must be a JSON list or CSV string.")

    @field_validator("trusted_proxies", mode="before")
    @classmethod
    def parse_trusted_proxies(cls, value: object) -> list[str]:
        if value is None:
            return []

        if isinstance(value, list):
            return [str(item) for item in value]

        if isinstance(value, str):
            return [
                item.strip()
                for item in value.split(",")
                if item.strip()
            ]

        raise ValueError("TRUSTED_PROXIES must be a CSV string.")

    @property
    def effective_geoip_license_key(self) -> str | None:
        """Allow GEOIP_API_KEY as a compatibility alias."""
        return self.geoip_license_key


@lru_cache
def get_settings() -> Settings:
    return Settings()