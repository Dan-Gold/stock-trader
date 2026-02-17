"""Celery application configuration."""

from celery import Celery
from celery.signals import after_setup_logger, after_setup_task_logger

from stock_trader.core.backtest import finalize_backtest_job, run_backtest  # noqa: F401, register tasks with Celery
from stock_trader.core.market_data.fetch_market_data import fetch_market_data  # noqa: F401, register tasks with Celery
from stock_trader.entrypoints.config import get_config
from stock_trader.logging import setup_logging

config = get_config()

celery_app = Celery(
    main="stock_trader",
    broker=f"redis://{config.redis_host}:{config.redis_port}/{config.celery_broker_redis_db}",
    backend=f"redis://{config.redis_host}:{config.redis_port}/{config.celery_backend_redis_db}",
    broker_connection_retry_on_startup=True,
)


celery_app.conf.update(
    accept_content=["json"],
    worker_concurrency=1,
    worker_max_tasks_per_child=1,  # TODO: Experiment with this
    worker_prefetch_multiplier=1,
    result_serializer="json",
    result_expires=config.celery_task_result_ttl,
    task_serializer="json",
    task_track_started=True,
    task_acks_late=True,
    task_queues=config.task_queues,
    task_routes=config.task_routes,
)


@after_setup_task_logger.connect
@after_setup_logger.connect
def configure_logger(**kwargs: object) -> None:
    """Configure logging after Celery sets up its own loggers."""
    setup_logging()
