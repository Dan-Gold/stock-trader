"""API server for Stock Trader application."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

import stock_trader.worker.celery_app  # noqa: F401, configure Celery broker for task dispatch
from stock_trader.api.exception_handlers import add_exception_handlers
from stock_trader.api.routes.backtest_router import router as backtest_router
from stock_trader.api.routes.health import router as health_router
from stock_trader.entrypoints.config import StockTraderConfig, get_config
from stock_trader.infrastructure.redis_client import RedisClient
from stock_trader.log_config import setup_logging

settings: StockTraderConfig = get_config()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifespan context manager for FastAPI application.

    This function is called on application startup and shutdown.

    Yields:
        None
    """
    # Startup
    setup_logging()
    logger.info("Stock Trader API starting up...")

    # Initialize Redis connection
    redis = RedisClient(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
    )
    await redis.connect()
    app.state.redis = redis

    yield

    # Shutdown
    logger.info("Stock Trader API shutting down...")
    await redis.close()


server = FastAPI(title="Stock Trader API", lifespan=lifespan)
server.include_router(backtest_router)
server.include_router(health_router)
add_exception_handlers(server)
