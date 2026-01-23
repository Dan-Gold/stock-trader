"""Main API router."""
from fastapi import APIRouter, FastAPI

from stock_trader.api.exception_handlers import add_exception_handlers
from stock_trader.api.routes.backtest import router as backtest_router

app = FastAPI(title="Stock Trader API")
router = APIRouter(prefix="/api")

router.include_router(backtest_router)


app.include_router(router)

add_exception_handlers(app)
