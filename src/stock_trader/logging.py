import logging

from stock_trader.entrypoints.config import get_config


def setup_logging() -> None:
    config = get_config()

    logging.basicConfig(
        level=config.log_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
