"""Debug routes for development and testing only."""

from fastapi import APIRouter, Depends

from stock_trader.api.dependencies import get_redis_client
from stock_trader.infrastructure.redis_client import IRedisClient

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/queue-length", summary="Get backtest queue length")
async def get_queue_length(
    redis: IRedisClient = Depends(get_redis_client),  # noqa: B008
) -> dict[str, str | int]:
    """Get the current number of jobs waiting in the backtest queue.

    Returns:
        Queue name and current length.
    """
    length = await redis.queue_length(queue="backtest_jobs")
    return {"queue": "backtest_jobs", "length": length}
