"""Unit tests for BacktestService."""

from uuid import uuid4

import pytest

from stock_trader.models.exceptions import JobAlreadyRunningError, JobNotFoundError
from stock_trader.models.shared_enums import BacktestStatusEnum
from tests.helpers import build_service, make_backtest_request
from tests.in_memory.in_memory_backtest_repo import MemoryBacktestRepository
from tests.in_memory.in_memory_task_dispatcher import MemoryTaskDispatcher

pytestmark = pytest.mark.asyncio


class TestCreateBacktestJob:
    """Tests for BacktestService.create_backtest_job."""

    async def test_returns_created_job(
        self,
        in_memory_repo: MemoryBacktestRepository,
        in_memory_dispatcher: MemoryTaskDispatcher,
    ) -> None:
        """The created job record is returned with correct fields."""
        service = build_service(in_memory_repo, in_memory_dispatcher)
        request = make_backtest_request(symbols=["TSLA", "AAPL"])

        job = await service.create_backtest_job(request)

        assert job.strategy_name == "bollinger_reversion"
        assert job.symbols == ["TSLA", "AAPL"]
        assert job.status == BacktestStatusEnum.CREATED

    async def test_persists_job_in_repository(
        self,
        in_memory_repo: MemoryBacktestRepository,
        in_memory_dispatcher: MemoryTaskDispatcher,
    ) -> None:
        """The created job is persisted in the repository."""
        service = build_service(in_memory_repo, in_memory_dispatcher)

        job = await service.create_backtest_job(make_backtest_request())

        assert job.uuid in in_memory_repo.jobs

    async def test_does_not_dispatch(
        self,
        in_memory_repo: MemoryBacktestRepository,
        in_memory_dispatcher: MemoryTaskDispatcher,
    ) -> None:
        """Creating a job should NOT automatically dispatch it."""
        service = build_service(in_memory_repo, in_memory_dispatcher)

        await service.create_backtest_job(make_backtest_request())

        assert in_memory_dispatcher.dispatches == []


class TestGetBacktestJob:
    """Tests for BacktestService.get_backtest_job."""

    async def test_returns_existing_job(
        self,
        in_memory_repo: MemoryBacktestRepository,
        in_memory_dispatcher: MemoryTaskDispatcher,
    ) -> None:
        """The service returns an existing job."""
        service = build_service(in_memory_repo, in_memory_dispatcher)
        created = await service.create_backtest_job(make_backtest_request())

        fetched = await service.get_backtest_job(created.uuid)

        assert fetched.uuid == created.uuid
        assert fetched.strategy_name == created.strategy_name

    async def test_raises_for_unknown_id(
        self,
        in_memory_repo: MemoryBacktestRepository,
        in_memory_dispatcher: MemoryTaskDispatcher,
    ) -> None:
        """Requesting a non-existent job should raise JobNotFoundError."""
        service = build_service(in_memory_repo, in_memory_dispatcher)

        with pytest.raises(JobNotFoundError):
            await service.get_backtest_job(uuid4())


class TestDispatchBacktestJob:
    """Tests for BacktestService.dispatch_backtest_job."""

    async def test_dispatches_to_task_queue(
        self,
        in_memory_repo: MemoryBacktestRepository,
        in_memory_dispatcher: MemoryTaskDispatcher,
    ) -> None:
        """A backtest job is dispatched to the task queue."""
        service = build_service(in_memory_repo, in_memory_dispatcher)
        job = await service.create_backtest_job(
            make_backtest_request(symbols=["PLTR", "MARA"]),
        )

        await service.dispatch_backtest_job(job.uuid)

        assert len(in_memory_dispatcher.dispatches) == 1
        dispatch = in_memory_dispatcher.dispatches[0]
        assert dispatch["job_id"] == str(job.uuid)
        assert dispatch["symbols"] == ["PLTR", "MARA"]

    async def test_sets_status_to_running(
        self,
        in_memory_repo: MemoryBacktestRepository,
        in_memory_dispatcher: MemoryTaskDispatcher,
    ) -> None:
        """Dispatching a job should update its status to RUNNING."""
        service = build_service(in_memory_repo, in_memory_dispatcher)
        job = await service.create_backtest_job(make_backtest_request())

        await service.dispatch_backtest_job(job.uuid)

        assert job.status == BacktestStatusEnum.RUNNING

    async def test_raises_if_already_running(
        self,
        in_memory_repo: MemoryBacktestRepository,
        in_memory_dispatcher: MemoryTaskDispatcher,
    ) -> None:
        """Dispatching a job that is already running should raise JobAlreadyRunningError."""
        service = build_service(in_memory_repo, in_memory_dispatcher)
        job = await service.create_backtest_job(make_backtest_request())
        await service.dispatch_backtest_job(job.uuid)

        with pytest.raises(JobAlreadyRunningError):
            await service.dispatch_backtest_job(job.uuid)

    async def test_allows_redispatch_after_completion(
        self,
        in_memory_repo: MemoryBacktestRepository,
        in_memory_dispatcher: MemoryTaskDispatcher,
    ) -> None:
        """A COMPLETED job can be re-dispatched (not blocked like RUNNING)."""
        service = build_service(in_memory_repo, in_memory_dispatcher)
        job = await service.create_backtest_job(make_backtest_request())

        # First dispatch then mark completed
        await service.dispatch_backtest_job(job.uuid)
        await in_memory_repo.update_job_status(job.uuid, BacktestStatusEnum.COMPLETED)

        # Second dispatch should succeed
        await service.dispatch_backtest_job(job.uuid)

        assert len(in_memory_dispatcher.dispatches) == 2

    async def test_allows_redispatch_after_failure(
        self,
        in_memory_repo: MemoryBacktestRepository,
        in_memory_dispatcher: MemoryTaskDispatcher,
    ) -> None:
        """A FAILED job can be re-dispatched."""
        service = build_service(in_memory_repo, in_memory_dispatcher)
        job = await service.create_backtest_job(make_backtest_request())

        await service.dispatch_backtest_job(job.uuid)
        await in_memory_repo.update_job_status(
            job.uuid,
            BacktestStatusEnum.FAILED,
            error="something broke",
        )

        await service.dispatch_backtest_job(job.uuid)

        assert len(in_memory_dispatcher.dispatches) == 2

    async def test_raises_for_unknown_job(
        self,
        in_memory_repo: MemoryBacktestRepository,
        in_memory_dispatcher: MemoryTaskDispatcher,
    ) -> None:
        """Dispatching a job that does not exist should raise JobNotFoundError."""
        service = build_service(in_memory_repo, in_memory_dispatcher)

        with pytest.raises(JobNotFoundError):
            await service.dispatch_backtest_job(uuid4())


class TestListBacktestJobs:
    """Tests for BacktestService.list_backtest_jobs."""

    async def test_returns_all_jobs(
        self,
        in_memory_repo: MemoryBacktestRepository,
        in_memory_dispatcher: MemoryTaskDispatcher,
    ) -> None:
        """All created jobs are returned by list_backtest_jobs."""
        service = build_service(in_memory_repo, in_memory_dispatcher)
        await service.create_backtest_job(make_backtest_request(symbols=["AAPL"]))
        await service.create_backtest_job(make_backtest_request(symbols=["TSLA"]))

        jobs = await service.list_backtest_jobs()

        assert len(jobs) == 2

    async def test_filters_by_status(
        self,
        in_memory_repo: MemoryBacktestRepository,
        in_memory_dispatcher: MemoryTaskDispatcher,
    ) -> None:
        """list_backtest_jobs can filter by job status."""
        service = build_service(in_memory_repo, in_memory_dispatcher)
        job1 = await service.create_backtest_job(make_backtest_request(symbols=["AAPL"]))
        await service.create_backtest_job(make_backtest_request(symbols=["TSLA"]))

        # Dispatch job1 so it becomes RUNNING
        await service.dispatch_backtest_job(job1.uuid)

        running = await service.list_backtest_jobs(status_filter=BacktestStatusEnum.RUNNING)
        created = await service.list_backtest_jobs(status_filter=BacktestStatusEnum.CREATED)

        assert len(running) == 1
        assert running[0].uuid == job1.uuid
        assert len(created) == 1

    async def test_pagination(
        self,
        in_memory_repo: MemoryBacktestRepository,
        in_memory_dispatcher: MemoryTaskDispatcher,
    ) -> None:
        """Pagination parameters offset and limit work as expected."""
        service = build_service(in_memory_repo, in_memory_dispatcher)
        for i in range(5):
            await service.create_backtest_job(make_backtest_request(symbols=[f"SYM{i}"]))

        page = await service.list_backtest_jobs(offset=2, limit=2)

        assert len(page) == 2

    async def test_empty_when_no_jobs(
        self,
        in_memory_repo: MemoryBacktestRepository,
        in_memory_dispatcher: MemoryTaskDispatcher,
    ) -> None:
        """list_backtest_jobs returns an empty list when no jobs exist."""
        service = build_service(in_memory_repo, in_memory_dispatcher)

        jobs = await service.list_backtest_jobs()

        assert jobs == []
