"""create stock_trader schema.

Revision ID: 0d583eb2b2f7
Revises:
Created Date: 2026-01-18 01:21:46.132014

"""

from typing import Sequence

from alembic import op

# Revision identifiers
revision: str = "0d583eb2b2f7"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade."""
    op.execute("CREATE SCHEMA IF NOT EXISTS stock_trader")


def downgrade() -> None:
    """Downgrade."""
    op.execute("DROP SCHEMA IF EXISTS stock_trader CASCADE")
