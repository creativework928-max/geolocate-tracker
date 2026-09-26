from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class GeoLocation(BaseModel):
    """
    Internal normalized geolocation model.

    This model represents the provider-independent result produced by
    the geolocation service.
    """

    model_config = ConfigDict(from_attributes=True)

    ip: str
    version: int

    country: str | None = None
    country_code: str | None = None
    region: str | None = None
    city: str | None = None
    postal_code: str | None = None

    latitude: float | None = None
    longitude: float | None = None

    timezone: str | None = None

    asn: str | None = None
    organization: str | None = None
    isp: str | None = None

    accuracy_radius_km: float | None = None

    is_vpn: bool | None = None
    is_proxy: bool | None = None
    is_tor: bool | None = None
    is_hosting: bool | None = None

    provider: str | None = None
    timestamp: datetime


class GeoLocationResponseData(BaseModel):
    """
    Public API representation of a geolocation result.
    """

    model_config = ConfigDict(from_attributes=True)

    ip: str
    version: int

    country: str | None = None
    country_code: str | None = None
    region: str | None = None
    city: str | None = None
    postal_code: str | None = None

    latitude: float | None = None
    longitude: float | None = None

    timezone: str | None = None

    asn: str | None = None
    organization: str | None = None
    isp: str | None = None

    accuracy_radius_km: float | None = None

    is_vpn: bool | None = None
    is_proxy: bool | None = None
    is_tor: bool | None = None
    is_hosting: bool | None = None


class GeoLocationResponseMeta(BaseModel):
    """
    Metadata associated with a successful lookup.
    """

    provider: str
    timestamp: datetime


class GeoLocationResponse(BaseModel):
    """
    Successful geolocation API response.
    """

    success: bool
    data: GeoLocationResponseData
    meta: GeoLocationResponseMeta


class ApiError(BaseModel):
    """
    Standard API error information.
    """

    code: str
    message: str


class ErrorResponse(BaseModel):
    """
    Standard failed API response.
    """

    success: bool = False
    error: ApiError


class HealthResponse(BaseModel):
    """
    Health endpoint response.
    """

    status: str
    service: str
