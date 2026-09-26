from __future__ import annotations

import ipaddress

from app.models.geolocation import GeoLocation
from app.providers.base import GeoLocationProvider
from app.services.cache_service import MemoryCache


class InvalidIPAddressError(ValueError):
    """Raised when an IP address is invalid."""


class NonPublicIPAddressError(ValueError):
    """Raised when an IP cannot be queried as a public GeoIP address."""


def parse_ip(value: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    """Parse and validate a textual IPv4/IPv6 address."""

    if not value or len(value) > 45:
        raise InvalidIPAddressError("Invalid IP address.")

    try:
        return ipaddress.ip_address(value.strip())
    except ValueError as exc:
        raise InvalidIPAddressError("Invalid IP address.") from exc


def is_public_ip(
    address: ipaddress.IPv4Address | ipaddress.IPv6Address,
) -> bool:
    """Return whether an IP is suitable for public GeoIP lookup."""

    return (
        address.is_global
        and not address.is_private
        and not address.is_loopback
        and not address.is_multicast
        and not address.is_unspecified
        and not address.is_reserved
        and not address.is_link_local
    )


def validate_public_ip(value: str) -> str:
    """Return canonical IP text or raise a validation exception."""

    address = parse_ip(value)

    if not is_public_ip(address):
        raise NonPublicIPAddressError(
            "Private or reserved IP addresses cannot be "
            "geolocated using the configured public GeoIP provider."
        )

    return str(address)


class GeoLocationService:
    """Application service coordinating validation, cache, and provider."""

    def __init__(
        self,
        provider: GeoLocationProvider,
        cache: MemoryCache[GeoLocation],
    ) -> None:
        self.provider = provider
        self.cache = cache

    async def lookup(self, value: str) -> GeoLocation:
        ip = validate_public_ip(value)

        cached = self.cache.get(ip)
        if cached is not None:
            return cached

        result = await self.provider.lookup(ip)
        self.cache.set(ip, result)

        return result