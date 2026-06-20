"""Health check route for liveness/readiness probes."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health", summary="Health check")
async def health() -> dict[str, str]:
    """Report that the API process is alive.

    Returns:
        A status payload for liveness/readiness probes.
    """
    return {"status": "ok"}
