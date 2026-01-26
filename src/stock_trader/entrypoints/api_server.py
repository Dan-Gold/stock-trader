"""API server for Stock Trader application."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from stock_trader.api.routes.backtest_router import router as backtest_router
from stock_trader.entrypoints.config import StockTraderConfig, get_config
from stock_trader.logging import setup_logging

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

    yield

    # Shutdown
    logger.info("Stock Trader API shutting down...")


server = FastAPI(title="Stock Trader API", lifespan=lifespan)
server.include_router(backtest_router)
