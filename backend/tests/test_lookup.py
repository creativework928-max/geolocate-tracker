import pytest

from app.models.geolocation import GeoLocation
from app.providers.base import (
    GeoLocationProvider,
    GeoLocationProviderTimeout,
)
from app.services.cache_service import MemoryCache
from app.services.geolocation_service import GeoLocationService


class MockGeoLocationProvider(GeoLocationProvider):
    name = "mock"

    def __init__(self, location: GeoLocation):
        self.location = location
        self.calls = 0

    async def lookup(self, ip: str) -> GeoLocation:
        self.calls += 1
        return self.location.model_copy(update={"ip": ip})


class TimeoutProvider(GeoLocationProvider):
    name = "mock-timeout"

    async def lookup(self, ip: str) -> GeoLocation:
        raise GeoLocationProviderTimeout("timeout")


@pytest.mark.asyncio
async def test_successful_lookup(sample_location):
    provider = MockGeoLocationProvider(sample_location)
    cache = MemoryCache(enabled=True, ttl_seconds=3600)

    service = GeoLocationService(provider, cache)

    result = await service.lookup("8.8.8.8")

    assert result.ip == "8.8.8.8"
    assert result.provider == "mock"


@pytest.mark.asyncio
async def test_lookup_uses_cache(sample_location):
    provider = MockGeoLocationProvider(sample_location)
    cache = MemoryCache(enabled=True, ttl_seconds=3600)

    service = GeoLocationService(provider, cache)

    await service.lookup("8.8.8.8")
    await service.lookup("8.8.8.8")

    assert provider.calls == 1


@pytest.mark.asyncio
async def test_provider_timeout_is_propagated():
    provider = TimeoutProvider()
    cache = MemoryCache(enabled=False, ttl_seconds=0)

    service = GeoLocationService(provider, cache)

    with pytest.raises(GeoLocationProviderTimeout):
        await service.lookup("8.8.8.8")