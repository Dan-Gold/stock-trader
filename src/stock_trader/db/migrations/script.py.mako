"""${message}.

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Created Date: ${create_date}

"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# Revision identifiers
revision: str = ${repr(up_revision)}
down_revision: str | Sequence[str] | None = ${repr(down_revision)}
branch_labels: str | Sequence[str] | None = ${repr(branch_labels)}
depends_on: str | Sequence[str] | None = ${repr(depends_on)}


def upgrade() -> None:
    """Upgrade."""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Downgrade."""
    ${downgrades if downgrades else "pass"}
