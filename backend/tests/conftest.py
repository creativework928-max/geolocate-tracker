from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.models.geolocation import GeoLocation


@pytest.fixture
def sample_location() -> GeoLocation:
    return GeoLocation(
        ip="8.8.8.8",
        version=4,
        country="United States",
        country_code="US",
        region="California",
        city="Mountain View",
        postal_code=None,
        latitude=37.4056,
        longitude=-122.0775,
        timezone="America/Los_Angeles",
        asn="AS15169",
        organization="Google LLC",
        isp="Google LLC",
        accuracy_radius_km=20.0,
        is_vpn=None,
        is_proxy=None,
        is_tor=None,
        is_hosting=None,
        connection_type=None,
        provider="mock",
        timestamp=datetime.now(timezone.utc),
    )