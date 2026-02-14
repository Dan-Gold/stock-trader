"""Main API router."""

from fastapi import APIRouter

from stock_trader.api.routes.backtest import router as backtest_router
from stock_trader.api.routes.debug import router as debug_router

router = APIRouter(prefix="/api")

router.include_router(backtest_router)
router.include_router(debug_router)
