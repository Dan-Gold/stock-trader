"""Alembic migration script."""

from alembic import context
from sqlalchemy import engine_from_config, pool

from stock_trader.db.db_helpers import get_database_url
from stock_trader.db.models import DatabaseModelBase
from stock_trader.entrypoints.config import get_config

config = context.config
target_metadata = DatabaseModelBase.metadata
settings = get_config()
db_url = get_database_url(settings.db_name, settings)


def run_migrations_offline(db_url: str) -> None:
    """Run migrations in 'offline' mode."""
    context.configure(
        url=db_url,
        target_metadata=target_metadata,
        include_schemas=True,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online(db_url: str) -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        url=db_url,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata, include_schemas=True, transaction_per_migration=True
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline(db_url)
else:
    run_migrations_online(db_url)
