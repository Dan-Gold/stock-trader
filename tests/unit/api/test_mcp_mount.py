"""Smoke test for the MCP tool surface.

Builds an app the same way ``api_server`` composes it (routers + FastApiMCP with
debug/health excluded by tag) and asserts the exposed tool list. Kept free of the
app module so it does not require the full runtime config.
"""

from fastapi import FastAPI
from fastapi_mcp import FastApiMCP

from stock_trader.api.routes.backtest_router import router as backtest_router
from stock_trader.api.routes.health import router as health_router


def _build_tool_names() -> set[str]:
    app = FastAPI(title="Stock Trader API")
    app.include_router(backtest_router)
    app.include_router(health_router)
    mcp = FastApiMCP(app, name="Stock Trader MCP", exclude_tags=["debug", "health"])
    return {tool.name for tool in mcp.tools}


class TestMcpToolSurface:
    """The mounted MCP server exposes the intended tools and hides the rest."""

    def test_includes_market_data_tool(self) -> None:
        """The new market-data primitive is exposed."""
        assert "get_market_data" in _build_tool_names()

    def test_includes_strategy_tools(self) -> None:
        """All strategy read endpoints are exposed with clean operation ids."""
        names = _build_tool_names()
        assert {
            "get_available_strategies",
            "get_strategy_parameter_schema",
            "get_all_strategies_and_parameters",
        } <= names

    def test_includes_backtest_tools(self) -> None:
        """The backtest create->run->poll flow is exposed."""
        names = _build_tool_names()
        assert {"create_backtest", "get_backtest", "dispatch_backtest", "list_backtests"} <= names

    def test_excludes_debug_and_health(self) -> None:
        """Debug and health endpoints are not exposed as tools."""
        names = _build_tool_names()
        assert not any("queue" in name for name in names)  # debug/queue-length
        assert not any("health" in name for name in names)
