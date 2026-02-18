"""Stock trader config."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class StockTraderConfig(BaseSettings):
    """Stock trader configuration settings."""

    # Logger
    log_level: int

    # Database settings
    db_username: str
    db_password: str
    db_name: str
    db_host: str
    db_port: int

    # Redis settings
    redis_host: str
    redis_port: int
    redis_db: int
    redis_ttl: int  # in seconds

    # Massive (formerly Polygon.io) API
    massive_api_key: str

    # Celery Config
    celery_broker_redis_db: int
    celery_backend_redis_db: int
    celery_task_result_ttl: int  # in seconds


@lru_cache
def get_config() -> StockTraderConfig:
    """Get stock trader configuration settings."""
    return StockTraderConfig()
