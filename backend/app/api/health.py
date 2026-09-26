from fastapi import APIRouter

from app.models.geolocation import HealthResponse


router = APIRouter(
    tags=["health"],
)


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
)
async def health_check() -> HealthResponse:
    """
    Return application health status.
    """
    return HealthResponse(
        status="healthy",
        service="geolocate-tracker",
    )
