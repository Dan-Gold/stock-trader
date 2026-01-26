"""Database engine and session setup."""

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from stock_trader.db.db_helpers import get_database_url
from stock_trader.entrypoints.config import get_config

config = get_config()

url = get_database_url(config.db_name, config, True)
database_engine = create_async_engine(url, pool_pre_ping=True)
database_session = async_sessionmaker(database_engine)

url_sync = get_database_url(config.db_name, config)
database_engine_sync = create_engine(url_sync, pool_pre_ping=True)
database_session_sync = sessionmaker(database_engine_sync)
