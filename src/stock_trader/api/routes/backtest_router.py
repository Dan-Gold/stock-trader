"""Main API router."""

from fastapi import APIRouter

from stock_trader.api.routes.backtest import router as backtest_router
from stock_trader.api.routes.debug import router as debug_router
from stock_trader.api.routes.market_data import router as market_data_router
from stock_trader.api.routes.strategy import router as strategy_router

router = APIRouter(prefix="/api")

router.include_router(backtest_router)
router.include_router(strategy_router)
router.include_router(market_data_router)
router.include_router(debug_router)
