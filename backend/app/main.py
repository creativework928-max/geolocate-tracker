from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.health import router as health_router
from app.api.routes import router as geolocation_router
from app.config import get_settings
from app.security.middleware import (
    add_security_headers,
    configure_security_middleware,
)


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format=(
        "%(asctime)s | %(levelname)s | "
        "%(name)s | %(message)s"
    ),
)

logger = logging.getLogger("geolocate-tracker")


# ---------------------------------------------------------------------------
# Application lifecycle
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """
    Application startup and shutdown lifecycle.

    Startup:
        - validates the application environment
        - logs non-sensitive runtime information
        - confirms frontend availability

    Shutdown:
        - logs application shutdown

    Secrets, API keys, client IP addresses, cookies, and authorization
    credentials are intentionally never logged.
    """

    logger.info(
        "Starting GeoLocate Tracker | environment=%s",
        settings.app_env,
    )

    if FRONTEND_DIR.exists():
        logger.info(
            "Frontend directory available: %s",
            FRONTEND_DIR,
        )
    else:
        logger.warning(
            "Frontend directory not found: %s",
            FRONTEND_DIR,
        )

    logger.info(
        "GeoIP provider configured: %s",
        settings.geoip_provider,
    )

    logger.info("GeoLocate Tracker startup complete.")

    try:
        yield
    finally:
        logger.info("GeoLocate Tracker shutting down.")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="GeoLocate Tracker",
    summary="IP Intelligence & Approximate Geolocation",
    description="""
GeoLocate Tracker is a privacy-conscious IP geolocation application.

It accepts public IPv4 and IPv6 addresses, resolves them through a
configured GeoIP provider, normalizes the provider response, and exposes
the result through a REST API and interactive browser dashboard.

## Important limitation

IP geolocation provides an **approximate geographic location**.

It does not identify:

- an exact street address
- an exact physical position
- a person's precise real-time location
- browser GPS coordinates

The application does not use browser GPS.

## Privacy

Client IP addresses are processed only as required to perform the
requested IP-based geolocation operation. Permanent storage is not
required by the application architecture.

Provider credentials remain on the backend and are never exposed to
browser JavaScript.
""",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

cors_origins = settings.cors_origins

if isinstance(cors_origins, str):
    cors_origins = [
        origin.strip()
        for origin in cors_origins.split(",")
        if origin.strip()
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
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


# ---------------------------------------------------------------------------
# Security middleware
# ---------------------------------------------------------------------------

configure_security_middleware(app)


# ---------------------------------------------------------------------------
# Request timing / privacy-conscious logging
# ---------------------------------------------------------------------------


@app.middleware("http")
async def request_logging_middleware(
    request: Request,
    call_next,
):
    """
    Record request duration without logging sensitive request data.

    Deliberately does not log:

        - client IP addresses
        - query strings
        - cookies
        - authorization headers
        - API keys
        - request bodies

    This is especially important for a privacy-oriented IP geolocation
    application.
    """

    start_time = time.perf_counter()

    try:
        response = await call_next(request)

    except Exception:
        duration_ms = (time.perf_counter() - start_time) * 1000

        logger.exception(
            "Unhandled request exception | method=%s | path=%s | duration_ms=%.2f",
            request.method,
            request.url.path,
            duration_ms,
        )

        raise

    duration_ms = (time.perf_counter() - start_time) * 1000

    logger.info(
        "Request completed | method=%s | path=%s | status=%s | duration_ms=%.2f",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )

    return response


# ---------------------------------------------------------------------------
# API routers
# ---------------------------------------------------------------------------

app.include_router(health_router)
app.include_router(geolocation_router)


# ---------------------------------------------------------------------------
# Frontend static files
# ---------------------------------------------------------------------------

FRONTEND_CSS_DIR = FRONTEND_DIR / "css"
FRONTEND_JS_DIR = FRONTEND_DIR / "js"
FRONTEND_ASSETS_DIR = FRONTEND_DIR / "assets"


if FRONTEND_CSS_DIR.exists():
    app.mount(
        "/css",
        StaticFiles(directory=FRONTEND_CSS_DIR),
        name="frontend-css",
    )


if FRONTEND_JS_DIR.exists():
    app.mount(
        "/js",
        StaticFiles(directory=FRONTEND_JS_DIR),
        name="frontend-js",
    )


if FRONTEND_ASSETS_DIR.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=FRONTEND_ASSETS_DIR),
        name="frontend-assets",
    )


# ---------------------------------------------------------------------------
# Browser application
# ---------------------------------------------------------------------------


@app.get(
    "/",
    include_in_schema=False,
)
async def serve_frontend():
    """
    Serve the GeoLocate Tracker browser application.
    """

    index_file = FRONTEND_DIR / "index.html"

    if not index_file.exists():
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "error": {
                    "code": "frontend_unavailable",
                    "message": "Frontend application is not available.",
                },
            },
        )

    return FileResponse(
        index_file,
        media_type="text/html",
    )


# ---------------------------------------------------------------------------
# Favicon
# ---------------------------------------------------------------------------


@app.get(
    "/favicon.ico",
    include_in_schema=False,
)
async def favicon():
    """
    Serve the favicon when one exists.

    Returning 204 instead of 404 keeps browser console output clean
    when the project does not provide a favicon yet.
    """

    favicon_file = FRONTEND_ASSETS_DIR / "favicon.svg"

    if favicon_file.exists():
        return FileResponse(
            favicon_file,
            media_type="image/svg+xml",
        )

    return JSONResponse(
        status_code=204,
        content=None,
    )


# ---------------------------------------------------------------------------
# Application status
# ---------------------------------------------------------------------------


@app.get(
    "/api/v1/status",
    include_in_schema=True,
    tags=["system"],
    summary="Application status",
)
async def application_status():
    """
    Return non-sensitive application information.

    This endpoint does not expose credentials or internal infrastructure
    details.
    """

    return {
        "success": True,
        "data": {
            "service": "geolocate-tracker",
            "status": "operational",
            "environment": settings.app_env,
            "provider": settings.geoip_provider,
        },
    }


# ---------------------------------------------------------------------------
# Global exception handler
# ---------------------------------------------------------------------------


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
):
    """
    Convert unexpected application errors into a safe JSON response.

    Internal exception details are logged server-side but never returned
    to the browser.
    """

    logger.exception(
        "Unhandled application error | method=%s | path=%s",
        request.method,
        request.url.path,
        exc_info=exc,
    )

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "internal_error",
                "message": "An unexpected server error occurred.",
            },
        },
    )


# ---------------------------------------------------------------------------
# Optional development diagnostics
# ---------------------------------------------------------------------------


@app.get(
    "/api/v1/config",
    include_in_schema=False,
)
async def safe_runtime_configuration():
    """
    Return intentionally limited runtime configuration.

    This endpoint is primarily useful during development.

    Sensitive configuration such as API keys, account IDs, secrets,
    trusted proxy details, and credentials is never returned.
    """

    return {
        "app_env": settings.app_env,
        "debug": settings.debug,
        "geoip_provider": settings.geoip_provider,
        "cache_enabled": settings.cache_enabled,
        "rate_limit_enabled": settings.rate_limit_enabled,
    }
