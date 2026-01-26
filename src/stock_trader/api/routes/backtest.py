"""Routes for backtesting trading strategies."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from stock_trader.api.dependencies import get_backtest_service
from stock_trader.api.services.backtest_service import BacktestService
from stock_trader.models.backtest_create_request import BacktestCreateRequest
from stock_trader.models.responses.backtest_create_response import BacktestCreateResponse
from stock_trader.models.responses.backtest_response import BacktestResponse
from stock_trader.models.shared_enums import BacktestStatusEnum

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/backtests", tags=["backtests"])


@router.post(
    "",
    response_model=BacktestCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create a new backtest job",
)
async def create_backtest(
    request: BacktestCreateRequest, backtest_service: BacktestService = Depends(get_backtest_service)
) -> BacktestCreateResponse:
    """Create a new backtest job.

    The job is created with PENDING status and queued for async processing.

    Args:
        request: The backtest configuration.
        backtest_service: The backtest service dependency.

    Returns:
        The created job's UUID and initial status.
    """
    job = await backtest_service.create_backtest_job(backtest_request=request)
    return BacktestCreateResponse(uuid=job.uuid, status=job.status)


@router.get(
    "/{job_id}",
    response_model=BacktestResponse,
    summary="Get backtest job status",
)
async def get_backtest(job_id: UUID) -> BacktestResponse:
    """Get the current status and details of a backtest job.

    Args:
        job_id: The UUID of the backtest job.

    Returns:
        The job details including current status.

    Raises:
        HTTPException: 404 if job not found.
    """
    # TODO: Fetch job from database
    raise NotImplementedError("Backtest retrieval not yet implemented")


@router.get(
    "",
    response_model=list[BacktestResponse],
    summary="List backtest jobs",
)
async def list_backtests(
    status_filter: BacktestStatusEnum | None = None,
    limit: int = Query(default=20, ge=1, le=100),
) -> list[BacktestResponse]:
    """List backtest jobs, optionally filtered by status.

    Args:
        status_filter: Optional status to filter by.
        limit: Maximum number of results (1-100).

    Returns:
        List of backtest jobs.
    """
    # TODO: Query jobs from database
    raise NotImplementedError("Backtest listing not yet implemented")
