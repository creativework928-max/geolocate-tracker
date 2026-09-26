from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.geolocation import GeoLocation


class GeoLocationProviderError(Exception):
    """Base exception for provider failures."""


class GeoLocationProviderTimeout(GeoLocationProviderError):
    """Provider request timed out."""


class GeoLocationProviderUnavailable(GeoLocationProviderError):
    """Provider is unavailable or returned a server-side error."""


class GeoLocationProviderNotFound(GeoLocationProviderError):
    """Provider has no record for the supplied IP."""


class GeoLocationProvider(ABC):
    """Provider abstraction used by the geolocation service."""

    name: str

    @abstractmethod
    async def lookup(self, ip: str) -> GeoLocation:
        """Resolve an IP into normalized geolocation data."""
        raise NotImplementedError