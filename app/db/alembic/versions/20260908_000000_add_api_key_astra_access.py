"""Add explicit per-key Astra permission, disabled for existing keys."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260908_000000_add_api_key_astra_access"
down_revision = "20260901_000000_merge_production_and_verbose_capture_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "api_keys",
        sa.Column("allow_gpt6_astra", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    with op.batch_alter_table("api_keys") as batch_op:
        batch_op.drop_column("allow_gpt6_astra")
