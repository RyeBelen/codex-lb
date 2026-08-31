"""merge production and verbose-capture migration heads

Revision ID: 20260901_000000_merge_production_and_verbose_capture_heads
Revises:
- 20260726_000000_repair_request_usage_rollups_after_merge
- 20260824_000000_add_api_key_verbose_capture
Create Date: 2026-09-01
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260901_000000_merge_production_and_verbose_capture_heads"
down_revision = (
    "20260726_000000_repair_request_usage_rollups_after_merge",
    "20260824_000000_add_api_key_verbose_capture",
)
branch_labels = None
depends_on = None

_REQUEST_LOGS_TABLE = "request_logs"
_API_KEY_TIME_ACCOUNT_INDEX = "idx_logs_api_key_time_account"


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(_REQUEST_LOGS_TABLE):
        return

    existing_indexes = {index["name"] for index in inspector.get_indexes(_REQUEST_LOGS_TABLE)}
    if _API_KEY_TIME_ACCOUNT_INDEX not in existing_indexes:
        op.create_index(
            _API_KEY_TIME_ACCOUNT_INDEX,
            _REQUEST_LOGS_TABLE,
            ["api_key_id", sa.text("requested_at DESC"), "account_id"],
            unique=False,
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(_REQUEST_LOGS_TABLE):
        return

    existing_indexes = {index["name"] for index in inspector.get_indexes(_REQUEST_LOGS_TABLE)}
    if _API_KEY_TIME_ACCOUNT_INDEX in existing_indexes:
        op.drop_index(_API_KEY_TIME_ACCOUNT_INDEX, table_name=_REQUEST_LOGS_TABLE)
