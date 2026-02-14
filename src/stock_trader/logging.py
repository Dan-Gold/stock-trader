"""Logging configuration for the stock trader application."""

import logging

from stock_trader.entrypoints.config import get_config


def setup_logging() -> None:
    """Set up logging configuration based on application settings."""
    config = get_config()

    logging.basicConfig(
        level=config.log_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        force=True,
    )
