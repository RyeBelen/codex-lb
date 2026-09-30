"""Add per-account weekly-exhaustion reset-credit auto-redeem preference."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260930_000000_add_weekly_empty_auto_redeem"
down_revision = "20260914_000000_add_model_account_routing"
branch_labels = None
depends_on = None

_TABLE = "accounts"
_COLUMN = "auto_redeem_reset_credits_when_weekly_exhausted"


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table(_TABLE) and _COLUMN not in {column["name"] for column in inspector.get_columns(_TABLE)}:
        with op.batch_alter_table(_TABLE) as batch_op:
            batch_op.add_column(sa.Column(_COLUMN, sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table(_TABLE) and _COLUMN in {column["name"] for column in inspector.get_columns(_TABLE)}:
        with op.batch_alter_table(_TABLE) as batch_op:
            batch_op.drop_column(_COLUMN)
