from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.health import router as health_router
from app.api.routes import router as api_router
from app.config import get_settings
from app.security.middleware import security_headers_middleware


settings = get_settings()

logging.basicConfig(
    level=getattr(settings, "log_level", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

limiter = Limiter(
    key_func=get_remote_address,
    enabled=settings.rate_limit_enabled,
)

app = FastAPI(
    title=settings.app_name,
    description=(
        "Real-time IP lookup and approximate GeoIP visualization API. "
        "IP geolocation is approximate and does not identify an exact "
        "physical address."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter


async def rate_limit_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={
            "success": False,
            "error": {
                "code": "rate_limit_exceeded",
                "message": "Rate limit exceeded. Please try again later.",
            },
        },
    )


app.add_exception_handler(
    RateLimitExceeded,
    rate_limit_handler,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["Accept", "Content-Type"],
)

app.middleware("http")(security_headers_middleware)

app.include_router(health_router)
app.include_router(api_router)


frontend_dir = Path(__file__).resolve().parents[2] / "frontend"

if frontend_dir.exists():
    app.mount(
        "/",
        StaticFiles(directory=str(frontend_dir), html=True),
        name="frontend",
    )
