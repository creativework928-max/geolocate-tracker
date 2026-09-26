from __future__ import annotations

import hashlib
import ipaddress
import logging
import os
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# Environment
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(ENV_FILE)


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def env_int(name: str, default: int) -> int:
    value = os.getenv(name)

    if value is None:
        return default

    try:
        return int(value)
    except ValueError:
        return default


APP_ENV = os.getenv("APP_ENV", "development")
DEBUG = env_bool("DEBUG", False)

GEOIP_PROVIDER = os.getenv(
    "GEOIP_PROVIDER",
    "maxmind",
).strip().lower()

GEOIP_API_KEY = os.getenv(
    "GEOIP_API_KEY",
    "",
).strip()

GEOIP_ACCOUNT_ID = os.getenv(
    "GEOIP_ACCOUNT_ID",
    "",
).strip()

GEOIP_BASE_URL = os.getenv(
    "GEOIP_BASE_URL",
    "https://geolite.info/geoip/v2.1",
).rstrip("/")

GEOIP_TIMEOUT_SECONDS = float(
    os.getenv(
        "GEOIP_TIMEOUT_SECONDS",
        "8",
    )
)

CACHE_ENABLED = env_bool(
    "CACHE_ENABLED",
    True,
)

CACHE_TTL_SECONDS = env_int(
    "CACHE_TTL_SECONDS",
    3600,
)

RATE_LIMIT_ENABLED = env_bool(
    "RATE_LIMIT_ENABLED",
    True,
)

RATE_LIMIT_PER_MINUTE = env_int(
    "RATE_LIMIT_PER_MINUTE",
    30,
)

LOG_LEVEL = os.getenv(
    "LOG_LEVEL",
    "INFO",
).upper()

MAP_TILE_URL = os.getenv(
    "MAP_TILE_URL",
    "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
)

MAP_ATTRIBUTION = os.getenv(
    "MAP_ATTRIBUTION",
    "© OpenStreetMap contributors",
)

TRUSTED_PROXIES_RAW = os.getenv(
    "TRUSTED_PROXIES",
    "",
).strip()

CORS_ORIGINS_RAW = os.getenv(
    "CORS_ORIGINS",
    "http://127.0.0.1:8000,http://localhost:8000",
)


# ============================================================================
# Logging
# ============================================================================

logging.basicConfig(
    level=getattr(
        logging,
        LOG_LEVEL,
        logging.INFO,
    ),
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(name)s | "
        "%(message)s"
    ),
)

logger = logging.getLogger("geolocate-tracker")


# ============================================================================
# Paths
# ============================================================================

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_DIR / "frontend"
INDEX_FILE = FRONTEND_DIR / "index.html"

CSS_DIR = FRONTEND_DIR / "css"
JS_DIR = FRONTEND_DIR / "js"
ASSETS_DIR = FRONTEND_DIR / "assets"


# ============================================================================
# Configuration helpers
# ============================================================================

def parse_csv(value: str) -> list[str]:
    return [
        item.strip()
        for item in value.split(",")
        if item.strip()
    ]


CORS_ORIGINS = parse_csv(CORS_ORIGINS_RAW)


def parse_trusted_proxies(value: str) -> list[ipaddress._BaseNetwork]:
    """
    Parse explicitly configured trusted proxy IPs/CIDRs.

    Forwarded headers are trusted only when the immediate peer belongs
    to one of these networks.
    """

    networks: list[ipaddress._BaseNetwork] = []

    if not value:
        return networks

    for item in parse_csv(value):
        try:
            networks.append(
                ipaddress.ip_network(
                    item,
                    strict=False,
                )
            )
        except ValueError:
            logger.warning(
                "Ignoring invalid trusted proxy entry."
            )

    return networks


TRUSTED_PROXY_NETWORKS = parse_trusted_proxies(
    TRUSTED_PROXIES_RAW,
)


# ============================================================================
# Exceptions
# ============================================================================

class InvalidIPAddressError(ValueError):
    """Raised when an IP address cannot be parsed."""


class NonPublicIPAddressError(ValueError):
    """Raised when an IP address is not publicly routable."""


class GeoProviderTimeoutError(RuntimeError):
    """Raised when the provider times out."""


class GeoProviderUnavailableError(RuntimeError):
    """Raised when the provider cannot return a valid result."""


# ============================================================================
# Data models
# ============================================================================

class GeoLocation(BaseModel):
    """
    Provider-independent normalized GeoIP result.
    """

    model_config = ConfigDict(from_attributes=True)

    ip: str
    version: int

    country: Optional[str] = None
    country_code: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None

    latitude: Optional[float] = None
    longitude: Optional[float] = None

    timezone: Optional[str] = None

    asn: Optional[str] = None
    organization: Optional[str] = None
    isp: Optional[str] = None

    accuracy_radius_km: Optional[float] = None

    is_vpn: Optional[bool] = None
    is_proxy: Optional[bool] = None
    is_tor: Optional[bool] = None
    is_hosting: Optional[bool] = None

    provider: Optional[str] = None
    timestamp: datetime


class GeoLocationResponseData(BaseModel):
    """
    Public API data object.
    """

    ip: str
    version: int

    country: Optional[str] = None
    country_code: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None

    latitude: Optional[float] = None
    longitude: Optional[float] = None

    timezone: Optional[str] = None

    asn: Optional[str] = None
    organization: Optional[str] = None
    isp: Optional[str] = None

    accuracy_radius_km: Optional[float] = None

    is_vpn: Optional[bool] = None
    is_proxy: Optional[bool] = None
    is_tor: Optional[bool] = None
    is_hosting: Optional[bool] = None


class GeoLocationMeta(BaseModel):
    provider: str
    timestamp: datetime


class GeoLocationResponse(BaseModel):
    success: bool
    data: GeoLocationResponseData
    meta: GeoLocationMeta


class ApiError(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    error: ApiError


class HealthResponse(BaseModel):
    status: str
    service: str


# ============================================================================
# IP validation
# ============================================================================

def parse_ip(value: str) -> ipaddress._BaseAddress:
    """
    Parse and validate an IPv4 or IPv6 address.
    """

    if not isinstance(value, str):
        raise InvalidIPAddressError(
            "IP address must be a string."
        )

    value = value.strip()

    if not value:
        raise InvalidIPAddressError(
            "IP address cannot be empty."
        )

    try:
        return ipaddress.ip_address(value)
    except ValueError as exc:
        raise InvalidIPAddressError(
            "Invalid IPv4 or IPv6 address."
        ) from exc


def is_public_ip(ip: ipaddress._BaseAddress) -> bool:
    """
    Return True only for publicly routable IP addresses.

    Private, loopback, multicast, unspecified, link-local, and reserved
    addresses are rejected.
    """

    return (
        ip.is_global
        and not ip.is_private
        and not ip.is_loopback
        and not ip.is_multicast
        and not ip.is_unspecified
        and not ip.is_link_local
        and not ip.is_reserved
    )


def validate_public_ip(value: str) -> ipaddress._BaseAddress:
    ip = parse_ip(value)

    if not is_public_ip(ip):
        raise NonPublicIPAddressError(
            "Private, reserved, loopback, multicast, link-local, "
            "or otherwise non-public IP addresses cannot be "
            "geolocated using the configured public GeoIP provider."
        )

    return ip


# ============================================================================
# Privacy helpers
# ============================================================================

def privacy_hash(value: str) -> str:
    """
    Produce a short non-reversible identifier for diagnostics.

    Full client IP addresses are never written to normal logs.
    """

    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()[:12]


# ============================================================================
# Client IP detection
# ============================================================================

def peer_is_trusted(
    request: Request,
) -> bool:
    """
    Determine whether forwarded headers may be trusted.

    If no trusted proxies are configured, forwarded headers are ignored.
    """

    if not TRUSTED_PROXY_NETWORKS:
        return False

    peer = request.client

    if peer is None:
        return False

    try:
        peer_ip = ipaddress.ip_address(peer.host)
    except ValueError:
        return False

    return any(
        peer_ip in network
        for network in TRUSTED_PROXY_NETWORKS
    )


def get_client_ip(request: Request) -> str:
    """
    Resolve the request's client IP.

    Forwarded headers are only trusted when the immediate connection
    originates from a configured trusted proxy.
    """

    peer = request.client

    if peer is None:
        return "0.0.0.0"

    peer_ip = peer.host

    if not peer_is_trusted(request):
        return peer_ip

    forwarded = request.headers.get(
        "X-Forwarded-For"
    )

    if forwarded:
        first = forwarded.split(",")[0].strip()

        try:
            ipaddress.ip_address(first)
            return first
        except ValueError:
            pass

    real_ip = request.headers.get(
        "X-Real-IP"
    )

    if real_ip:
        try:
            ipaddress.ip_address(real_ip.strip())
            return real_ip.strip()
        except ValueError:
            pass

    return peer_ip


# ============================================================================
# Cache
# ============================================================================

@dataclass
class CacheEntry:
    value: GeoLocation
    expires_at: float


class MemoryCache:
    """
    Small process-local TTL cache.

    This is appropriate for development and single-process deployments.
    Redis can replace this class later without changing the geolocation
    provider interface.
    """

    def __init__(
        self,
        ttl_seconds: int,
    ) -> None:
        self.ttl_seconds = max(
            1,
            ttl_seconds,
        )
        self._items: dict[str, CacheEntry] = {}

    def get(
        self,
        key: str,
    ) -> Optional[GeoLocation]:
        entry = self._items.get(key)

        if entry is None:
            return None

        if time.monotonic() >= entry.expires_at:
            self._items.pop(
                key,
                None,
            )
            return None

        return entry.value

    def set(
        self,
        key: str,
        value: GeoLocation,
    ) -> None:
        self._items[key] = CacheEntry(
            value=value,
            expires_at=(
                time.monotonic()
                + self.ttl_seconds
            ),
        )

    def clear(self) -> None:
        self._items.clear()


cache = MemoryCache(
    ttl_seconds=CACHE_TTL_SECONDS,
)


# ============================================================================
# Rate limiter
# ============================================================================

class MemoryRateLimiter:
    """
    Simple fixed-window process-local rate limiter.

    For multiple production instances, use Redis or another shared store.
    """

    def __init__(
        self,
        limit: int,
        window_seconds: int = 60,
    ) -> None:
        self.limit = max(1, limit)
        self.window_seconds = max(
            1,
            window_seconds,
        )
        self._requests: dict[
            str,
            list[float],
        ] = defaultdict(list)

    def allow(
        self,
        key: str,
    ) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds

        timestamps = self._requests[key]

        self._requests[key] = [
            timestamp
            for timestamp in timestamps
            if timestamp > cutoff
        ]

        if len(self._requests[key]) >= self.limit:
            return False

        self._requests[key].append(now)

        return True


rate_limiter = MemoryRateLimiter(
    limit=RATE_LIMIT_PER_MINUTE,
)


# ============================================================================
# Provider abstraction
# ============================================================================

class GeoLocationProvider:
    """
    Provider abstraction.

    A different provider can be introduced by implementing lookup().
    """

    name = "base"

    async def lookup(
        self,
        ip: str,
    ) -> GeoLocation:
        raise NotImplementedError


class MaxMindProvider(GeoLocationProvider):
    """
    MaxMind-compatible GeoIP API adapter.

    The default endpoint is configured for the GeoLite/MaxMind-style
    city endpoint used by the project.

    Provider credentials are always read server-side.
    """

    name = "maxmind"

    def __init__(
        self,
        base_url: str,
        api_key: str,
        account_id: str,
        timeout: float,
    ) -> None:
        self.base_url = base_url
        self.api_key = api_key
        self.account_id = account_id
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": (
                "GeoLocate-Tracker/1.0"
            ),
        }

        if self.api_key:
            headers["Authorization"] = (
                f"Bearer {self.api_key}"
            )

        return headers

    async def lookup(
        self,
        ip: str,
    ) -> GeoLocation:
        url = (
            f"{self.base_url}/city/{ip}"
        )

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=False,
            ) as client:
                response = await client.get(
                    url,
                    headers=self._headers(),
                )

        except httpx.TimeoutException as exc:
            raise GeoProviderTimeoutError(
                "The geolocation provider timed out."
            ) from exc

        except httpx.HTTPError as exc:
            raise GeoProviderUnavailableError(
                "The geolocation provider could not be reached."
            ) from exc

        if response.status_code == 401:
            raise GeoProviderUnavailableError(
                "The geolocation provider rejected the credentials."
            )

        if response.status_code == 403:
            raise GeoProviderUnavailableError(
                "The geolocation provider denied the request."
            )

        if response.status_code == 404:
            raise GeoProviderUnavailableError(
                "The requested IP was not found by the provider."
            )

        if response.status_code == 429:
            raise GeoProviderUnavailableError(
                "The geolocation provider rate limit was exceeded."
            )

        if response.status_code >= 500:
            raise GeoProviderUnavailableError(
                "The geolocation provider is temporarily unavailable."
            )

        if response.status_code != 200:
            raise GeoProviderUnavailableError(
                "The geolocation provider returned an unexpected response."
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise GeoProviderUnavailableError(
                "The geolocation provider returned invalid JSON."
            ) from exc

        return normalize_provider_response(
            ip=ip,
            payload=payload,
            provider=self.name,
        )


def normalize_provider_response(
    ip: str,
    payload: dict[str, Any],
    provider: str,
) -> GeoLocation:
    """
    Normalize a MaxMind/GeoIP-style response.

    Missing fields remain None. No geographic information is fabricated.
    """

    country = payload.get("country") or {}
    country_names = country.get("names") or {}

    subdivisions = payload.get(
        "subdivisions"
    ) or []

    subdivision = (
        subdivisions[0]
        if subdivisions
        else {}
    )

    subdivision_names = (
        subdivision.get("names")
        or {}
    )

    city = payload.get("city") or {}
    city_names = city.get("names") or {}

    postal = payload.get(
        "postal"
    ) or {}

    location = payload.get(
        "location"
    ) or {}

    traits = payload.get(
        "traits"
    ) or {}

    continent = payload.get(
        "continent"
    ) or {}

    latitude = location.get(
        "latitude"
    )

    longitude = location.get(
        "longitude"
    )

    accuracy = location.get(
        "accuracy_radius"
    )

    accuracy_radius_km: Optional[float]

    if accuracy is None:
        accuracy_radius_km = None
    else:
        try:
            accuracy_radius_km = float(
                accuracy
            )
        except (
            TypeError,
            ValueError,
        ):
            accuracy_radius_km = None

    asn_number = traits.get(
        "autonomous_system_number"
    )

    asn = (
        f"AS{asn_number}"
        if asn_number is not None
        else None
    )

    organization = (
        traits.get(
            "autonomous_system_organization"
        )
    )

    isp = (
        traits.get("isp")
        or traits.get("organization")
    )

    is_vpn = traits.get(
        "is_anonymous_vpn"
    )

    is_proxy = traits.get(
        "is_anonymous_proxy"
    )

    is_tor = traits.get(
        "is_tor_exit_node"
    )

    is_hosting = traits.get(
        "is_hosting_provider"
    )

    timezone = location.get(
        "time_zone"
    )

    country_code = (
        country.get("iso_code")
    )

    return GeoLocation(
        ip=ip,
        version=ipaddress.ip_address(ip).version,
        country=country_names.get("en"),
        country_code=country_code,
        region=subdivision_names.get("en"),
        city=city_names.get("en"),
        postal_code=postal.get("code"),
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        asn=asn,
        organization=organization,
        isp=isp,
        accuracy_radius_km=accuracy_radius_km,
        is_vpn=is_vpn,
        is_proxy=is_proxy,
        is_tor=is_tor,
        is_hosting=is_hosting,
        provider=provider,
        timestamp=datetime.now(
            timezone.utc
        ),
    )


# ============================================================================
# Provider factory
# ============================================================================

def create_provider() -> GeoLocationProvider:
    if GEOIP_PROVIDER == "maxmind":
        return MaxMindProvider(
            base_url=GEOIP_BASE_URL,
            api_key=GEOIP_API_KEY,
            account_id=GEOIP_ACCOUNT_ID,
            timeout=GEOIP_TIMEOUT_SECONDS,
        )

    raise RuntimeError(
        f"Unsupported GEOIP_PROVIDER: "
        f"{GEOIP_PROVIDER}"
    )


provider = create_provider()


# ============================================================================
# Geolocation service
# ============================================================================

class GeoLocationService:
    """
    Coordinates validation, caching, provider access, and normalization.
    """

    async def lookup(
        self,
        value: str,
    ) -> GeoLocation:
        ip_object = validate_public_ip(
            value
        )

        normalized_ip = str(
            ip_object
        )

        if CACHE_ENABLED:
            cached = cache.get(
                normalized_ip
            )

            if cached is not None:
                return cached

        result = await provider.lookup(
            normalized_ip
        )

        if CACHE_ENABLED:
            cache.set(
                normalized_ip,
                result,
            )

        return result


geo_service = GeoLocationService()


# ============================================================================
# FastAPI lifecycle
# ============================================================================

@asynccontextmanager
async def lifespan(
    application: FastAPI,
):
    logger.info(
        "Starting GeoLocate Tracker."
    )

    logger.info(
        "Environment: %s",
        APP_ENV,
    )

    logger.info(
        "GeoIP provider: %s",
        GEOIP_PROVIDER,
    )

    logger.info(
        "Caching enabled: %s",
        CACHE_ENABLED,
    )

    logger.info(
        "Rate limiting enabled: %s",
        RATE_LIMIT_ENABLED,
    )

    if not INDEX_FILE.exists():
        logger.warning(
            "Frontend index.html not found: %s",
            INDEX_FILE,
        )

    yield

    cache.clear()

    logger.info(
        "GeoLocate Tracker stopped."
    )


# ============================================================================
# Application
# ============================================================================

app = FastAPI(
    title="GeoLocate Tracker",
    version="1.0.0",
    summary="IP Intelligence & Approximate Geolocation",
    description="""
# GeoLocate Tracker

A privacy-conscious IP geolocation application.

GeoLocate Tracker performs **real-time IP lookups**, not continuous
physical tracking.

IP geolocation provides an approximate geographic location. It does not
identify a user's exact address or physical position.

The application does not use browser GPS.

## Main capabilities

- IPv4 lookup
- IPv6 lookup
- Automatic requesting-client IP detection
- GeoIP provider abstraction
- Optional caching
- Rate limiting
- Interactive Leaflet map
- Accuracy-radius visualization
- REST API
- OpenAPI documentation

## Privacy

Provider credentials remain on the backend.

Client IP addresses are not permanently stored by this application
by default.

## API

- `GET /health`
- `GET /api/v1/health`
- `GET /api/v1/lookup/{ip}`
- `GET /api/v1/my-location`
""",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# ============================================================================
# CORS
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=[
        "GET",
        "OPTIONS",
    ],
    allow_headers=[
        "Accept",
        "Content-Type",
        "Origin",
    ],
)


# ============================================================================
# Security headers
# ============================================================================

@app.middleware("http")
async def security_headers(
    request: Request,
    call_next,
):
    response = await call_next(
        request
    )

    response.headers[
        "X-Content-Type-Options"
    ] = "nosniff"

    response.headers[
        "X-Frame-Options"
    ] = "DENY"

    response.headers[
        "Referrer-Policy"
    ] = "strict-origin-when-cross-origin"

    response.headers[
        "Permissions-Policy"
    ] = (
        "geolocation=(), "
        "camera=(), "
        "microphone=()"
    )

    response.headers[
        "Cross-Origin-Opener-Policy"
    ] = "same-origin"

    response.headers[
        "Cross-Origin-Resource-Policy"
    ] = "same-origin"

    if APP_ENV == "production":
        response.headers[
            "Strict-Transport-Security"
        ] = (
            "max-age=31536000; "
            "includeSubDomains"
        )

    return response


# ============================================================================
# Privacy-conscious request logging
# ============================================================================

@app.middleware("http")
async def request_logging(
    request: Request,
    call_next,
):
    started = time.perf_counter()

    try:
        response = await call_next(
            request
        )

    except Exception:
        duration = (
            time.perf_counter()
            - started
        ) * 1000

        logger.exception(
            "Unhandled request | "
            "method=%s path=%s "
            "duration_ms=%.2f",
            request.method,
            request.url.path,
            duration,
        )

        raise

    duration = (
        time.perf_counter()
        - started
    ) * 1000

    logger.info(
        "Request | method=%s path=%s "
        "status=%s duration_ms=%.2f",
        request.method,
        request.url.path,
        response.status_code,
        duration,
    )

    return response


# ============================================================================
# Rate limiting middleware
# ============================================================================

@app.middleware("http")
async def rate_limit(
    request: Request,
    call_next,
):
    """
    Rate-limit only expensive geolocation endpoints.

    The client identifier is hashed before being used by the limiter.
    """

    if (
        RATE_LIMIT_ENABLED
        and request.url.path.startswith(
            "/api/v1/"
        )
        and request.url.path in {
            "/api/v1/my-location",
        }
        or (
            RATE_LIMIT_ENABLED
            and request.url.path.startswith(
                "/api/v1/lookup/"
            )
        )
    ):
        client_ip = get_client_ip(
            request
        )

        identifier = privacy_hash(
            client_ip
        )

        if not rate_limiter.allow(
            identifier
        ):
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": {
                        "code": "rate_limit_exceeded",
                        "message": (
                            "Too many lookup requests. "
                            "Please try again later."
                        ),
                    },
                },
            )

    return await call_next(
        request
    )


# ============================================================================
# Health
# ============================================================================

@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["health"],
    summary="Application health",
)
async def health() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        service="geolocate-tracker",
    )


@app.get(
    "/api/v1/health",
    response_model=HealthResponse,
    tags=["health"],
    summary="API health",
)
async def api_health() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        service="geolocate-tracker",
    )


# ============================================================================
# Successful response helper
# ============================================================================

def make_success_response(
    result: GeoLocation,
) -> GeoLocationResponse:
    data = GeoLocationResponseData.model_validate(
        result
    )

    return GeoLocationResponse(
        success=True,
        data=data,
        meta=GeoLocationMeta(
            provider=result.provider or "unknown",
            timestamp=result.timestamp,
        ),
    )


# ============================================================================
# Error response helper
# ============================================================================

def make_error(
    status_code: int,
    code: str,
    message: str,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "code": code,
                "message": message,
            },
        },
    )


# ============================================================================
# IP lookup
# ============================================================================

@app.get(
    "/api/v1/lookup/{ip}",
    response_model=GeoLocationResponse,
    tags=["geolocation"],
    summary="Look up an IPv4 or IPv6 address",
    responses={
        400: {
            "model": ErrorResponse,
        },
        404: {
            "model": ErrorResponse,
        },
        429: {
            "model": ErrorResponse,
        },
        502: {
            "model": ErrorResponse,
        },
        504: {
            "model": ErrorResponse,
        },
    },
)
async def lookup_ip(
    ip: str,
):
    """
    Look up a public IPv4 or IPv6 address.
    """

    try:
        result = await geo_service.lookup(
            ip
        )

    except InvalidIPAddressError as exc:
        return make_error(
            400,
            "invalid_ip",
            str(exc),
        )

    except NonPublicIPAddressError as exc:
        return make_error(
            400,
            "non_public_ip",
            str(exc),
        )

    except GeoProviderTimeoutError:
        logger.warning(
            "GeoIP provider timeout."
        )

        return make_error(
            504,
            "provider_timeout",
            "The geolocation provider timed out.",
        )

    except GeoProviderUnavailableError:
        logger.warning(
            "GeoIP provider unavailable."
        )

        return make_error(
            502,
            "provider_unavailable",
            "The geolocation provider is temporarily unavailable.",
        )

    except Exception:
        logger.exception(
            "Unexpected lookup failure."
        )

        return make_error(
            500,
            "internal_error",
            "An unexpected server error occurred.",
        )

    return make_success_response(
        result
    )


# ============================================================================
# Automatic client IP detection
# ============================================================================

@app.get(
    "/api/v1/my-location",
    response_model=GeoLocationResponse,
    tags=["geolocation"],
    summary="Detect and geolocate the requesting client's IP",
)
async def my_location(
    request: Request,
):
    """
    Determine the requesting client's IP and geolocate it.

    Browser GPS is not used.
    """

    client_ip = get_client_ip(
        request
    )

    return await lookup_ip(
        ip=client_ip
    )


# ============================================================================
# Public runtime status
# ============================================================================

@app.get(
    "/api/v1/status",
    tags=["system"],
    summary="Application status",
)
async def status():
    return {
        "success": True,
        "data": {
            "service": "geolocate-tracker",
            "status": "operational",
            "environment": APP_ENV,
            "provider": GEOIP_PROVIDER,
            "cache_enabled": CACHE_ENABLED,
            "rate_limit_enabled": RATE_LIMIT_ENABLED,
        },
    }


# ============================================================================
# Frontend
# ============================================================================

@app.get(
    "/",
    include_in_schema=False,
)
async def frontend():
    """
    Serve the browser application.
    """

    if INDEX_FILE.exists():
        return FileResponse(
            INDEX_FILE,
            media_type="text/html",
        )

    return HTMLResponse(
        content=FALLBACK_HTML,
        status_code=200,
    )


# ============================================================================
# Static resources
# ============================================================================

if CSS_DIR.exists():
    app.mount(
        "/css",
        StaticFiles(
            directory=CSS_DIR
        ),
        name="css",
    )


if JS_DIR.exists():
    app.mount(
        "/js",
        StaticFiles(
            directory=JS_DIR
        ),
        name="js",
    )


if ASSETS_DIR.exists():
    app.mount(
        "/assets",
        StaticFiles(
            directory=ASSETS_DIR
        ),
        name="assets",
    )


# ============================================================================
# Favicon
# ============================================================================

@app.get(
    "/favicon.ico",
    include_in_schema=False,
)
async def favicon():
    favicon_file = (
        ASSETS_DIR / "favicon.svg"
    )

    if favicon_file.exists():
        return FileResponse(
            favicon_file,
            media_type="image/svg+xml",
        )

    return JSONResponse(
        status_code=204,
        content=None,
    )


# ============================================================================
# Global exception handler
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception,
):
    logger.exception(
        "Unhandled application exception | "
        "method=%s path=%s",
        request.method,
        request.url.path,
    )

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "internal_error",
                "message": (
                    "An unexpected server error occurred."
                ),
            },
        },
    )


# ============================================================================
# Minimal fallback browser application
# ============================================================================
#
# This fallback is only used if frontend/index.html does not exist.
# The normal project uses frontend/index.html + CSS + JS.
#

FALLBACK_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>GeoLocate Tracker</title>

<style>
:root {
    --bg: #07111f;
    --surface: #0d1b2a;
    --surface-2: #13263a;
    --primary: #38bdf8;
    --success: #34d399;
    --danger: #fb7185;
    --text: #f8fafc;
    --muted: #94a3b8;
}

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    min-height: 100vh;
    font-family:
        Inter,
        ui-sans-serif,
        system-ui,
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;

    background:
        radial-gradient(
            circle at top right,
            rgba(56, 189, 248, .12),
            transparent 32%
        ),
        var(--bg);

    color: var(--text);
}

.container {
    width: min(1180px, calc(100% - 32px));
    margin: 0 auto;
    padding: 40px 0;
}

.header {
    margin-bottom: 28px;
}

.badge {
    display: inline-flex;
    padding: 7px 12px;
    border-radius: 999px;
    background: rgba(52, 211, 153, .1);
    color: var(--success);
    font-size: 12px;
    font-weight: 700;
    letter-spacing: .08em;
    text-transform: uppercase;
}

h1 {
    margin: 14px 0 8px;
    font-size: clamp(32px, 5vw, 58px);
    line-height: 1;
}

.subtitle {
    color: var(--muted);
    font-size: 17px;
}

.search {
    display: flex;
    gap: 12px;
    padding: 18px;
    background: rgba(13, 27, 42, .88);
    border: 1px solid rgba(148, 163, 184, .14);
    border-radius: 18px;
}

input {
    flex: 1;
    min-width: 0;
    padding: 14px 16px;
    border: 1px solid rgba(148, 163, 184, .18);
    border-radius: 12px;
    background: var(--surface-2);
    color: var(--text);
    font-size: 16px;
    outline: none;
}

input:focus {
    border-color: var(--primary);
    box-shadow: 0 0 0 3px rgba(56, 189, 248, .12);
}

button {
    border: 0;
    border-radius: 12px;
    padding: 0 20px;
    background: var(--primary);
    color: #032033;
    font-weight: 800;
    cursor: pointer;
}

button:hover {
    filter: brightness(1.08);
}

button:disabled {
    opacity: .55;
    cursor: not-allowed;
}

.panel {
    margin-top: 20px;
    padding: 24px;
    background: rgba(13, 27, 42, .88);
    border: 1px solid rgba(148, 163, 184, .14);
    border-radius: 18px;
}

.grid {
    display: grid;
    grid-template-columns:
        repeat(auto-fit, minmax(190px, 1fr));
    gap: 14px;
}

.card {
    padding: 18px;
    background: var(--surface-2);
    border-radius: 14px;
}

.label {
    color: var(--muted);
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: .08em;
}

.value {
    margin-top: 8px;
    font-size: 18px;
    font-weight: 700;
    overflow-wrap: anywhere;
}

.notice {
    margin-top: 20px;
    padding: 14px 16px;
    border-radius: 12px;
    background: rgba(56, 189, 248, .08);
    color: var(--muted);
    line-height: 1.6;
}

.error {
    color: var(--danger);
}

@media (max-width: 700px) {
    .search {
        flex-direction: column;
    }

    button {
        min-height: 48px;
    }
}
</style>
</head>

<body>

<main class="container">

<header class="header">
    <span class="badge">IP Intelligence</span>

    <h1>GeoLocate Tracker</h1>

    <p class="subtitle">
        Approximate IP-based geographic intelligence.
    </p>
</header>

<section class="search">
    <input
        id="ip"
        type="text"
        inputmode="text"
        autocomplete="off"
        placeholder="Enter IPv4 or IPv6 address"
        value="8.8.8.8"
    >

    <button id="locate">
        Locate IP
    </button>

    <button id="detect">
        Detect My IP
    </button>
</section>

<section
    id="message"
    class="notice"
    aria-live="polite"
>
    Enter an IP address to explore its approximate geographic location.
</section>

<section
    id="result"
    class="panel"
    hidden
>
    <div class="grid">

        <div class="card">
            <div class="label">IP Address</div>
            <div class="value" id="r-ip">—</div>
        </div>

        <div class="card">
            <div class="label">IP Version</div>
            <div class="value" id="r-version">—</div>
        </div>

        <div class="card">
            <div class="label">Country</div>
            <div class="value" id="r-country">—</div>
        </div>

        <div class="card">
            <div class="label">Region</div>
            <div class="value" id="r-region">—</div>
        </div>

        <div class="card">
            <div class="label">City</div>
            <div class="value" id="r-city">—</div>
        </div>

        <div class="card">
            <div class="label">Timezone</div>
            <div class="value" id="r-timezone">—</div>
        </div>

        <div class="card">
            <div class="label">Coordinates</div>
            <div class="value" id="r-coordinates">—</div>
        </div>

        <div class="card">
            <div class="label">Accuracy Radius</div>
            <div class="value" id="r-accuracy">—</div>
        </div>

        <div class="card">
            <div class="label">ISP</div>
            <div class="value" id="r-isp">—</div>
        </div>

        <div class="card">
            <div class="label">ASN</div>
            <div class="value" id="r-asn">—</div>
        </div>

    </div>

    <div class="notice">
        IP geolocation provides an approximate geographic location.
        It does not identify an exact physical address or position.
    </div>
</section>

</main>

<script>
const $ = (id) => document.getElementById(id);

const ipInput = $("ip");
const locateButton = $("locate");
const detectButton = $("detect");
const message = $("message");
const result = $("result");

function safeValue(value) {
    return value === null ||
           value === undefined ||
           value === ""
        ? "—"
        : String(value);
}

function render(data) {
    $("r-ip").textContent =
        safeValue(data.ip);

    $("r-version").textContent =
        data.version
            ? "IPv" + data.version
            : "—";

    $("r-country").textContent =
        data.country_code
            ? `${safeValue(data.country)}
               (${data.country_code})`
            : safeValue(data.country);

    $("r-region").textContent =
        safeValue(data.region);

    $("r-city").textContent =
        safeValue(data.city);

    $("r-timezone").textContent =
        safeValue(data.timezone);

    if (
        data.latitude !== null &&
        data.latitude !== undefined &&
        data.longitude !== null &&
        data.longitude !== undefined
    ) {
        $("r-coordinates").textContent =
            `${data.latitude}, ${data.longitude}`;
    } else {
        $("r-coordinates").textContent = "—";
    }

    $("r-accuracy").textContent =
        data.accuracy_radius_km !== null &&
        data.accuracy_radius_km !== undefined
            ? `${data.accuracy_radius_km} km`
            : "Not provided";

    $("r-isp").textContent =
        safeValue(data.isp);

    $("r-asn").textContent =
        safeValue(data.asn);

    result.hidden = false;
}

async function request(url) {
    locateButton.disabled = true;
    detectButton.disabled = true;

    message.className = "notice";
    message.textContent =
        "Resolving IP location...";

    try {
        const response =
            await fetch(url);

        let payload;

        try {
            payload =
                await response.json();
        } catch {
            throw new Error(
                "The server returned invalid JSON."
            );
        }

        if (!response.ok) {
            throw new Error(
                payload?.error?.message ||
                "The request failed."
            );
        }

        render(payload.data);

        message.textContent =
            "Location resolved successfully.";

    } catch (error) {
        result.hidden = true;
        message.className =
            "notice error";

        message.textContent =
            error.message ||
            "Unable to resolve the IP address.";

    } finally {
        locateButton.disabled = false;
        detectButton.disabled = false;
    }
}

locateButton.addEventListener(
    "click",
    () => {
        const ip =
            ipInput.value.trim();

        if (!ip) {
            message.className =
                "notice error";

            message.textContent =
                "Please enter an IPv4 or IPv6 address.";

            return;
        }

        request(
            "/api/v1/lookup/" +
            encodeURIComponent(ip)
        );
    }
);

detectButton.addEventListener(
    "click",
    () => {
        request(
            "/api/v1/my-location"
        );
    }
);

ipInput.addEventListener(
    "keydown",
    (event) => {
        if (event.key === "Enter") {
            locateButton.click();
        }
    }
);
</script>

</body>
</html>
"""


# ============================================================================
# End of application
# ============================================================================
