from __future__ import annotations

import ipaddress
from datetime import datetime, timezone

import httpx

from app.config import Settings
from app.models.geolocation import GeoLocation
from app.providers.base import (
    GeoLocationProvider,
    GeoLocationProviderNotFound,
    GeoLocationProviderTimeout,
    GeoLocationProviderUnavailable,
)


class MaxMindProvider(GeoLocationProvider):
    """MaxMind GeoIP/GeoLite web-service adapter."""

    name = "maxmind"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

        if not settings.geoip_account_id:
            raise ValueError(
                "GEOIP_ACCOUNT_ID is required for the MaxMind provider."
            )

        if not settings.effective_geoip_license_key:
            raise ValueError(
                "GEOIP_LICENSE_KEY is required for the MaxMind provider."
            )

        service = settings.geoip_service.lower().strip()

        if service not in {"city", "country", "insights"}:
            raise ValueError(
                "GEOIP_SERVICE must be city, country, or insights."
            )

        self.service = service

        if service == "city":
            host = "geolite.info"
        else:
            host = "geoip.maxmind.com"

        self.base_url = (
            f"https://{host}/geoip/v2.1/{self.service}"
        )

    async def lookup(self, ip: str) -> GeoLocation:
        """Query MaxMind and normalize the response."""

        url = f"{self.base_url}/{ip}"

        try:
            async with httpx.AsyncClient(
                timeout=self.settings.geoip_timeout_seconds,
                follow_redirects=False,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "GeoLocate-Tracker/1.0",
                },
                auth=(
                    self.settings.geoip_account_id,
                    self.settings.effective_geoip_license_key,
                ),
            ) as client:
                response = await client.get(url)

        except httpx.TimeoutException as exc:
            raise GeoLocationProviderTimeout(
                "MaxMind request timed out."
            ) from exc

        except httpx.HTTPError as exc:
            raise GeoLocationProviderUnavailable(
                "MaxMind request failed."
            ) from exc

        if response.status_code in {404, 400}:
            raise GeoLocationProviderNotFound(
                "MaxMind has no usable record for this IP."
            )

        if response.status_code in {401, 403, 429} or response.status_code >= 500:
            raise GeoLocationProviderUnavailable(
                f"MaxMind returned HTTP {response.status_code}."
            )

        if response.status_code >= 400:
            raise GeoLocationProviderUnavailable(
                f"MaxMind returned HTTP {response.status_code}."
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise GeoLocationProviderUnavailable(
                "MaxMind returned invalid JSON."
            ) from exc

        return self._normalize(ip, payload)

    def _normalize(
        self,
        ip: str,
        payload: dict,
    ) -> GeoLocation:
        parsed_ip = ipaddress.ip_address(ip)

        country = payload.get("country") or {}
        continent = payload.get("continent") or {}
        city = payload.get("city") or {}
        location = payload.get("location") or {}
        postal = payload.get("postal") or {}
        subdivision = self._first_subdivision(payload)
        traits = payload.get("traits") or {}

        country_name = country.get("names", {}).get("en")
        country_code = country.get("iso_code")

        region = (
            subdivision.get("names", {}).get("en")
            if subdivision
            else None
        )

        city_name = city.get("names", {}).get("en")

        latitude = self._float_or_none(location.get("latitude"))
        longitude = self._float_or_none(location.get("longitude"))

        radius = self._float_or_none(
            location.get("accuracy_radius")
        )

        asn_number = traits.get("autonomous_system_number")
        asn = (
            f"AS{asn_number}"
            if asn_number is not None
            else None
        )

        return GeoLocation(
            ip=str(parsed_ip),
            version=parsed_ip.version,
            country=country_name,
            country_code=country_code,
            region=region,
            city=city_name,
            postal_code=postal.get("code"),
            latitude=latitude,
            longitude=longitude,
            timezone=location.get("time_zone"),
            asn=asn,
            organization=traits.get(
                "autonomous_system_organization"
            ),
            isp=traits.get("isp"),
            accuracy_radius_km=(
                radius if radius is None else radius
            ),
            is_vpn=self._bool_or_none(
                traits.get("is_anonymous_vpn")
            ),
            is_proxy=self._bool_or_none(
                traits.get("is_anonymous_proxy")
            ),
            is_tor=self._bool_or_none(
                traits.get("is_tor_exit_node")
            ),
            is_hosting=self._bool_or_none(
                traits.get("is_hosting_provider")
            ),
            connection_type=traits.get("connection_type"),
            provider=self.name,
            timestamp=datetime.now(timezone.utc),
        )

    @staticmethod
    def _first_subdivision(payload: dict) -> dict:
        subdivisions = payload.get("subdivisions") or []
        return subdivisions[0] if subdivisions else {}

    @staticmethod
    def _float_or_none(value: object) -> float | None:
        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _bool_or_none(value: object) -> bool | None:
        if value is None:
            return None

        if isinstance(value, bool):
            return value

        return None