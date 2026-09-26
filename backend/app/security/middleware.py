from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from fastapi import Request, Response


ASGIHandler = Callable[[Request], Awaitable[Response]]


async def security_headers_middleware(
    request: Request,
    call_next: ASGIHandler,
) -> Response:
    """Add conservative browser security headers."""

    start = time.perf_counter()

    response = await call_next(request)

    duration = time.perf_counter() - start

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "geolocation=(), camera=(), microphone=()"
    )
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' https://unpkg.com; "
        "style-src 'self' https://unpkg.com; "
        "img-src 'self' data: https://*.tile.openstreetmap.org; "
        "connect-src 'self'; "
        "font-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "frame-ancestors 'none'"
    )
    response.headers["X-Process-Time"] = f"{duration:.4f}"

    return response