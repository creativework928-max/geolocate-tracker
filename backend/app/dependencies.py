from __future__ import annotations

import ipaddress
from typing import Annotated

from fastapi import Depends, HTTPException, Request

from app.config import Settings, get_settings
from app.models.geolocation import GeoLocation
from app.providers.base import GeoLocationProvider
from app.providers.maxmind import MaxMindProvider
from app.services.cache_service import MemoryCache
from app.services.geolocation_service import GeoLocationService


def get_app_settings() -> Settings:
    return get_settings()


def build_provider(settings: Settings) -> GeoLocationProvider:
    if settings.demo_mode:
        return DemoGeoLocationProvider()

    provider = settings.geoip_provider.lower().strip()

    if provider == "maxmind":
        return MaxMindProvider(settings)

    raise ValueError(f"Unsupported GEOIP_PROVIDER: {provider}")


def get_cache(
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> MemoryCache[GeoLocation]:
    return MemoryCache(
        enabled=settings.cache_enabled,
        ttl_seconds=settings.cache_ttl_seconds,
    )


def get_geo_service(
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> GeoLocationService:
    # A process-level singleton would be preferable for a high-throughput
    # service; FastAPI's dependency cache is intentionally kept simple here.
    provider = build_provider(settings)

    return GeoLocationService(
        provider=provider,
        cache=MemoryCache(
            enabled=settings.cache_enabled,
            ttl_seconds=settings.cache_ttl_seconds,
        ),
    )


def get_client_ip(
    request: Request,
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> str:
    """Resolve the client IP without blindly trusting forwarded headers.

    If the immediate peer is not explicitly trusted, forwarded headers are
    ignored. For a trusted reverse-proxy chain, X-Forwarded-For is examined
    from right to left and the first untrusted address is selected.
    """

    peer = request.client.host if request.client else None

    if not peer:
        raise HTTPException(
            status_code=400,
            detail="Unable to determine client IP.",
        )

    if not settings.trusted_proxies:
        return peer

    trusted = _trusted_networks(settings.trusted_proxies)

    try:
        peer_ip = ipaddress.ip_address(peer)
    except ValueError:
        return peer

    if not _in_networks(peer_ip, trusted):
        return peer

    forwarded = request.headers.get("x-forwarded-for")

    if not forwarded:
        real_ip = request.headers.get("x-real-ip")
        return real_ip.strip() if real_ip else peer

    candidates = [
        item.strip()
        for item in forwarded.split(",")
        if item.strip()
    ]

    for candidate in reversed(candidates):
        try:
            candidate_ip = ipaddress.ip_address(candidate)
        except ValueError:
            continue

        if not _in_networks(candidate_ip, trusted):
            return str(candidate_ip)

    return peer


def _trusted_networks(
    values: list[str],
) -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    networks = []

    for value in values:
        try:
            networks.append(
                ipaddress.ip_network(value, strict=False)
            )
        except ValueError:
            continue

    return networks


def _in_networks(
    address: ipaddress.IPv4Address | ipaddress.IPv6Address,
    networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network],
) -> bool:
    return any(address in network for network in networks)


class DemoGeoLocationProvider(GeoLocationProvider):
    """Explicitly labeled deterministic development provider."""

    name = "demo"

    async def lookup(self, ip: str) -> GeoLocation:
        from datetime import datetime, timezone

        address = ipaddress.ip_address(ip)

        return GeoLocation(
            ip=ip,
            version=address.version,
            country="Demo Country",
            country_code="DM",
            region="Demo Region",
            city="Demo City",
            postal_code=None,
            latitude=25.2048,
            longitude=55.2708,
            timezone="UTC",
            asn="AS65000",
            organization="DEMO DATA",
            isp="DEMO DATA",
            accuracy_radius_km=50.0,
            provider=self.name,
            timestamp=datetime.now(timezone.utc),
        )