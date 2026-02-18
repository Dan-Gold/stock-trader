"""Database engine and session setup.

Uses @lru_cache factory functions so engines/sessions are created lazily on
first use rather than at import time.
"""

from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from stock_trader.db.db_helpers import get_database_url
from stock_trader.entrypoints.config import get_config


@lru_cache
def get_async_session_maker() -> async_sessionmaker:
    """Return the async session maker for the API layer."""
    config = get_config()
    url = get_database_url(config.db_name, config, is_async=True)
    engine = create_async_engine(url, pool_pre_ping=True)
    return async_sessionmaker(engine)


@lru_cache
def get_sync_session_maker() -> sessionmaker:
    """Return the sync session maker for Celery tasks."""
    config = get_config()
    url = get_database_url(config.db_name, config)
    engine = create_engine(url, pool_pre_ping=True)
    return sessionmaker(engine)
