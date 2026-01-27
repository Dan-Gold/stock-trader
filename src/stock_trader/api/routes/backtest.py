"""Routes for backtesting trading strategies."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from stock_trader.api.dependencies import get_backtest_service
from stock_trader.api.services.backtest_service import BacktestService
from stock_trader.db.models.backtest_jobs import BacktestJobTableSchema
from stock_trader.models.backtest_create_request import BacktestCreateRequest
from stock_trader.models.responses.backtest_create_response import BacktestCreateResponse
from stock_trader.models.responses.backtest_response import BacktestResponse
from stock_trader.models.shared_enums import BacktestStatusEnum

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/backtests", tags=["backtests"])

# TODO: Consider in the future creating a domain model and UI model


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
async def get_backtest(job_id: UUID, backtest_service: BacktestService = Depends(get_backtest_service)) -> BacktestResponse:
    """Get the current status and details of a backtest job.

    Args:
        job_id: The UUID of the backtest job.
        backtest_service: The backtest service dependency.

    Returns:
        The job details including current status.

    Raises:
        HTTPException: 404 if job not found.
    """
    job: BacktestJobTableSchema = await backtest_service.get_backtest_job(job_id=job_id)
    return BacktestResponse(
        uuid=job.uuid,
        status=job.status,
        strategy_name=job.strategy_name,
        symbols=job.symbols,
        parameters=job.parameters,
        error=job.error,
        create_time=job.create_time,
        start_time=job.start_time,
        end_time=job.end_time,
    )


@router.get(
    "",
    response_model=list[BacktestResponse],
    summary="List backtest jobs",
)
async def list_backtests(
    backtest_service: BacktestService = Depends(get_backtest_service),
    status_filter: BacktestStatusEnum | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[BacktestResponse]:
    """List backtest jobs with pagination.

    Args:
        backtest_service: The backtest service dependency.
        status_filter: Optional status to filter by.
        offset: Number of records to skip (0-indexed).
        limit: Maximum number of results to return (1-100).

    Returns:
        List of backtest jobs.
    """
    jobs = await backtest_service.list_backtest_jobs(
        status_filter=status_filter,
        offset=offset,
        limit=limit,
    )

    return [
        BacktestResponse(
            uuid=job.uuid,
            status=job.status,
            strategy_name=job.strategy_name,
            symbols=job.symbols,
            parameters=job.parameters,
            error=job.error,
            create_time=job.create_time,
            start_time=job.start_time,
            end_time=job.end_time,
        )
        for job in jobs
    ]
