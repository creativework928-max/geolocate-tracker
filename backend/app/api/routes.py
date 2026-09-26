from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.config import Settings
from app.dependencies import (
    get_app_settings,
    get_client_ip,
    get_geo_service,
)
from app.models.geolocation import (
    ErrorResponse,
    GeoLocationResponse,
    GeoLocationResponseData,
    GeoLocationResponseMeta,
)
from app.providers.base import (
    GeoLocationProviderNotFound,
    GeoLocationProviderTimeout,
    GeoLocationProviderUnavailable,
)
from app.services.geolocation_service import (
    GeoLocationService,
    InvalidIPAddressError,
    NonPublicIPAddressError,
)


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1",
    tags=["geolocation"],
)


def success_response(result: Any) -> GeoLocationResponse:
    """
    Convert the internal GeoLocation model into the public API response.

    The service returns a GeoLocation instance, while the API exposes
    GeoLocationResponseData. Explicit conversion keeps the internal
    service model separate from the external API contract.
    """
    data = GeoLocationResponseData.model_validate(result)

    return GeoLocationResponse(
        success=True,
        data=data,
        meta=GeoLocationResponseMeta(
            provider=result.provider or "unknown",
            timestamp=result.timestamp,
        ),
    )


def error_response(
    status_code: int,
    code: str,
    message: str,
) -> JSONResponse:
    """
    Return a consistent API error response.
    """
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


async def perform_lookup(
    ip: str,
    service: GeoLocationService,
) -> GeoLocationResponse | JSONResponse:
    """
    Perform a geolocation lookup and translate service/provider errors
    into stable HTTP API responses.

    Keeping this logic in one place prevents /lookup/{ip} and
    /my-location from duplicating error handling.
    """
    try:
        result = await service.lookup(ip)

    except InvalidIPAddressError as exc:
        return error_response(
            status.HTTP_400_BAD_REQUEST,
            "invalid_ip",
            str(exc),
        )

    except NonPublicIPAddressError as exc:
        return error_response(
            status.HTTP_400_BAD_REQUEST,
            "non_public_ip",
            str(exc),
        )

    except GeoLocationProviderNotFound as exc:
        return error_response(
            status.HTTP_404_NOT_FOUND,
            "provider_not_found",
            str(exc),
        )

    except GeoLocationProviderTimeout:
        logger.warning("GeoIP provider timeout.")
        return error_response(
            status.HTTP_504_GATEWAY_TIMEOUT,
            "provider_timeout",
            "The geolocation provider timed out.",
        )

    except GeoLocationProviderUnavailable:
        logger.warning("GeoIP provider unavailable.")
        return error_response(
            status.HTTP_502_BAD_GATEWAY,
            "provider_unavailable",
            "The geolocation provider is temporarily unavailable.",
        )

    except Exception:
        logger.exception("Unexpected geolocation lookup failure.")
        return error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "internal_error",
            "An unexpected server error occurred.",
        )

    return success_response(result)


@router.get(
    "/lookup/{ip}",
    response_model=GeoLocationResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        504: {"model": ErrorResponse},
    },
    summary="Look up an IPv4 or IPv6 address",
    description=(
        "Returns the approximate geographic location associated with "
        "a public IPv4 or IPv6 address. IP geolocation does not "
        "identify an exact physical location or street address."
    ),
)
async def lookup_ip(
    ip: str,
    service: GeoLocationService = Depends(get_geo_service),
):
    """
    Look up an explicitly supplied public IP address.
    """
    return await perform_lookup(
        ip=ip,
        service=service,
    )


@router.get(
    "/my-location",
    response_model=GeoLocationResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        504: {"model": ErrorResponse},
    },
    summary="Detect and geolocate the requesting client's public IP",
    description=(
        "Determines the requesting client's IP using the configured "
        "trusted-proxy rules and returns its approximate GeoIP location. "
        "This endpoint does not use browser GPS."
    ),
)
async def my_location(
    request: Request,
    settings: Settings = Depends(get_app_settings),
    service: GeoLocationService = Depends(get_geo_service),
):
    """
    Detect the client's IP and perform a geolocation lookup.

    The request object must remain available because get_client_ip()
    uses it to determine the appropriate client address.
    """
    client_ip = get_client_ip(
        request,
        settings,
    )

    return await perform_lookup(
        ip=client_ip,
        service=service,
    )
