"""Create the database if it does not exist and apply migrations."""

import logging

import sqlalchemy_utils

from stock_trader.db.db_helpers import apply_migrations, get_database_url
from stock_trader.entrypoints.config import get_config
from stock_trader.log_config import setup_logging

logger = logging.getLogger(__name__)


def create_database(db_name: str, db_url: str) -> bool:
    """Create the database if it does not exist."""
    logger.info(f"Creating database '{db_name}' if it does not exist...")

    if sqlalchemy_utils.database_exists(db_url):
        logger.info(f"Database '{db_name}' already exists.")
        return False

    sqlalchemy_utils.create_database(db_url)
    logger.info(f"Database '{db_name}' created successfully.")
    return True


if __name__ == "__main__":
    setup_logging()
    settings = get_config()

    db_name = settings.db_name
    db_url = get_database_url(db_name, settings)

    create_database(db_name, db_url)
    apply_migrations(db_name, db_url)
