"""add immutable legacy request-log daily aggregates

Revision ID: 20260714_030000_add_request_log_legacy_daily_aggregates
Revises: 20260714_020000_add_request_log_historical_facts
Create Date: 2026-07-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260714_030000_add_request_log_legacy_daily_aggregates"
down_revision = "20260714_020000_add_request_log_historical_facts"
branch_labels = None
depends_on = None

_TABLE = "request_log_legacy_daily_aggregates"
_INDEXES = (
    ("idx_legacy_request_aggregates_date", ["bucket_date"]),
    ("idx_legacy_request_aggregates_account_date", ["account_id", "bucket_date"]),
    ("idx_legacy_request_aggregates_api_key_date", ["api_key_id", "bucket_date"]),
)


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if not inspector.has_table(_TABLE):
        op.create_table(
            _TABLE,
            sa.Column("aggregate_key", sa.String(length=64), nullable=False),
            sa.Column("bucket_date", sa.Date(), nullable=False),
            sa.Column("api_key_id", sa.String(), nullable=True),
            sa.Column("account_id", sa.String(), nullable=True),
            sa.Column("model", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("error_code", sa.String(), nullable=True),
            sa.Column("request_kind", sa.String(), nullable=False),
            sa.Column("service_tier", sa.String(), nullable=True),
            sa.Column("requested_service_tier", sa.String(), nullable=True),
            sa.Column("actual_service_tier", sa.String(), nullable=True),
            sa.Column("transport", sa.String(), nullable=True),
            sa.Column("upstream_transport", sa.String(), nullable=True),
            sa.Column("source", sa.String(), nullable=True),
            sa.Column("useragent_group", sa.String(), nullable=True),
            sa.Column("plan_type", sa.String(), nullable=True),
            sa.Column("is_deleted", sa.Boolean(), nullable=False),
            sa.Column("request_count", sa.BigInteger(), nullable=False),
            sa.Column("error_count", sa.BigInteger(), nullable=False),
            sa.Column("input_tokens", sa.BigInteger(), nullable=False),
            sa.Column("output_tokens", sa.BigInteger(), nullable=False),
            sa.Column("effective_output_tokens", sa.BigInteger(), nullable=False),
            sa.Column("cached_input_tokens", sa.BigInteger(), nullable=False),
            sa.Column("reasoning_tokens", sa.BigInteger(), nullable=False),
            sa.Column("cost_usd", sa.Float(), nullable=False),
            sa.Column("cost_microdollars", sa.BigInteger(), nullable=False),
            sa.Column("account_request_count", sa.BigInteger(), nullable=False),
            sa.Column("account_input_tokens", sa.BigInteger(), nullable=False),
            sa.Column("account_output_tokens", sa.BigInteger(), nullable=False),
            sa.Column("account_cached_input_tokens", sa.BigInteger(), nullable=False),
            sa.Column("account_cost_usd", sa.Float(), nullable=False),
            sa.Column("latency_ms_sum", sa.BigInteger(), nullable=False),
            sa.Column("latency_ms_count", sa.BigInteger(), nullable=False),
            sa.Column("latency_first_token_ms_sum", sa.BigInteger(), nullable=False),
            sa.Column("latency_first_token_ms_count", sa.BigInteger(), nullable=False),
            sa.Column("source_snapshot_sha256", sa.String(length=64), nullable=False),
            sa.Column("source_row_sha256", sa.String(length=64), nullable=False),
            sa.Column("imported_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("aggregate_key"),
        )
        inspector = sa.inspect(connection)

    existing_indexes = {str(index["name"]) for index in inspector.get_indexes(_TABLE)}
    for name, columns in _INDEXES:
        if name not in existing_indexes:
            op.create_index(name, _TABLE, columns, unique=False)


def downgrade() -> None:
    # Recovery data is forward-only. Older code safely ignores this table, and
    # a downgrade must not silently destroy the only surviving dated history.
    pass
