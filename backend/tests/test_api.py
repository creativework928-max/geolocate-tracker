from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.dependencies import get_geo_service
from app.main import app
from app.models.geolocation import GeoLocation
from app.services.cache_service import MemoryCache
from app.services.geolocation_service import GeoLocationService
from app.providers.base import GeoLocationProvider


class MockProvider(GeoLocationProvider):
    name = "mock"

    async def lookup(self, ip: str) -> GeoLocation:
        return GeoLocation(
            ip=ip,
            version=4,
            country="Test Country",
            country_code="TC",
            region="Test Region",
            city="Test City",
            latitude=1.0,
            longitude=2.0,
            timezone="UTC",
            asn="AS65001",
            organization="Test Org",
            isp="Test ISP",
            accuracy_radius_km=10.0,
            provider="mock",
            timestamp=datetime.now(timezone.utc),
        )


def override_service():
    return GeoLocationService(
        provider=MockProvider(),
        cache=MemoryCache(enabled=False, ttl_seconds=0),
    )


app.dependency_overrides[get_geo_service] = override_service

client = TestClient(app)


def test_lookup_api_success():
    response = client.get("/api/v1/lookup/8.8.8.8")

    assert response.status_code == 200

    payload = response.json()

    assert payload["success"] is True
    assert payload["data"]["ip"] == "8.8.8.8"
    assert payload["data"]["country"] == "Test Country"


def test_lookup_api_invalid_ip():
    response = client.get("/api/v1/lookup/not-an-ip")

    assert response.status_code == 400

    payload = response.json()

    assert payload["success"] is False
    assert payload["error"]["code"] == "invalid_ip"


def test_lookup_api_private_ip():
    response = client.get("/api/v1/lookup/192.168.1.1")

    assert response.status_code == 400

    payload = response.json()

    assert payload["error"]["code"] == "non_public_ip"