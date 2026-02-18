"""Helper functions for database operations."""

import logging
from pathlib import Path
from urllib.parse import quote_plus

from alembic import command
from alembic.config import Config as AlembicConfig

from stock_trader.entrypoints.config import StockTraderConfig

logger = logging.getLogger(__name__)


def get_database_url(db_name: str, config: StockTraderConfig, is_async: bool = False) -> str:
    """Generate a database URL from configuration settings."""
    encode_password = quote_plus(config.db_password)

    if is_async:
        return f"postgresql+asyncpg://{config.db_username}:{encode_password}@{config.db_host}:{config.db_port}/{db_name}"

    return f"postgresql://{config.db_username}:{encode_password}@{config.db_host}:{config.db_port}/{db_name}"


def apply_migrations(db_name: str, db_url: str) -> None:
    """Apply database migrations using Alembic."""
    logger.info(f"Applying {db_name} database migrations...")

    alembic_ini_path = Path(__file__).parent / "migrations" / "alembic.ini"
    logger.info(f"Alembic ini path: {alembic_ini_path}")
    alembic_cfg = AlembicConfig(str(alembic_ini_path))
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)

    command.upgrade(alembic_cfg, "head")
    logger.info(f"Database migrations for {db_name} applied successfully.")
